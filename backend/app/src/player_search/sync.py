"""Keeps the in-memory player search index in sync with MongoDB.

Guarantees:
- A player added or removed through the API is found, or gone, as soon as
  upsert or remove returns. The routes call them right after their Mongo
  write, before responding.
- Renames and deactivations by the data scraper, which never calls the API,
  show up within one refresh interval.
- A refresh never undoes an API change made while its Mongo snapshot was
  loading. Every API change is logged with a generation number, and a
  snapshot only overrides players nobody changed since it started.
- The API starts even if the first build fails. Search answers 503 until a
  background retry succeeds, and adds made in the meantime are replayed onto
  the new index.

NOTE Only valid with a single API process. A second uvicorn worker or API
replica would hold its own index and miss the other one's adds until its
next refresh. Publish adds and removes over Redis before scaling out.
"""

import asyncio
import time
from contextlib import suppress
from typing import NamedTuple

from mongo import MongoConn, get_tracked_players

from .index import PlayerSearchIndex, SearchResult
from .normalize import normalize_tag

# Snapshot diffs are applied in chunks, handing the event loop back between
# them, so a big batch of scraper renames cannot stall requests.
_DIFF_CHUNK = 2000


class SearchIndexNotReady(Exception):
    """The first index build has not succeeded yet."""


class _Change(NamedTuple):
    generation: int
    tag: str
    name: str | None
    removed: bool


class PlayerSearchService:
    """Owns the search index, its startup build and its periodic refresh."""

    def __init__(self, mongo: MongoConn, refresh_interval_s: float, retry_s: float):
        self._mongo = mongo
        self._refresh_interval_s = refresh_interval_s
        self._retry_s = retry_s
        self._index: PlayerSearchIndex | None = None
        self._generation = 0
        # tag key -> latest API change. Kept until a snapshot that started
        # after the change has been applied, which then already contains it.
        self._changes: dict[str, _Change] = {}
        self._task: asyncio.Task | None = None

    @property
    def ready(self) -> bool:
        return self._index is not None

    async def start(self) -> None:
        """Build the index once, then keep refreshing it in the background.

        A failed first build is logged, not raised: the rest of the API does
        not depend on search.
        """

        try:
            await self.refresh()
        except Exception as e:
            print(f"[WARNING] [SEARCH] Initial index build failed, retrying: {e}")
        self._task = asyncio.create_task(self._refresh_loop())

    async def close(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task

    def search(self, query: str, limit: int) -> list[SearchResult]:
        """Search the index. See PlayerSearchIndex.search.

        Raises:
            SearchIndexNotReady: If no build has succeeded yet.
        """

        if self._index is None:
            raise SearchIndexNotReady()
        return self._index.search(query, limit)

    def upsert(self, tag: str, name: str | None) -> None:
        """Index a player the API just stored as tracked. Never raises.

        HAS to be called after the Mongo write: a refresh whose snapshot
        started before this call trusts the logged change over the snapshot.
        """

        self._log_change(tag, name, removed=False)
        if self._index is None:
            return
        try:
            self._index.upsert(tag, name)
        except Exception as e:
            # The player is stored; the next refresh indexes them.
            print(f"[ERROR] [SEARCH] Could not index {tag}: {e}")

    def remove(self, tag: str) -> None:
        """Drop a player the API just deactivated. Never raises.

        HAS to be called after the Mongo write, like upsert.
        """

        self._log_change(tag, None, removed=True)
        if self._index is None:
            return
        try:
            self._index.remove(tag)
        except Exception as e:
            print(f"[ERROR] [SEARCH] Could not remove {tag} from the index: {e}")

    def _log_change(self, tag: str, name: str | None, removed: bool) -> None:
        self._generation += 1
        self._changes[normalize_tag(tag)] = _Change(
            self._generation, tag, name, removed
        )

    def _changed_since(self, tag: str, generation: int) -> bool:
        change = self._changes.get(normalize_tag(tag))
        return change is not None and change.generation > generation

    async def refresh(self) -> None:
        """Bring the index up to date with the tracked players in Mongo.

        The first call builds the index in a worker thread. Later calls apply
        only the differences, on the event loop, in chunks.

        Raises:
            Exception: If the Mongo read or the build fails. The current
                index stays in place.
        """

        started = self._generation
        players = await get_tracked_players(self._mongo)

        if self._index is None:
            began = time.perf_counter()
            index = await asyncio.to_thread(PlayerSearchIndex.build, players.items())
            # Adds and removes made during the build are missing from it.
            for change in sorted(self._changes.values()):
                if change.generation > started:
                    if change.removed:
                        index.remove(change.tag)
                    else:
                        index.upsert(change.tag, change.name)
            self._index = index
            stats = index.stats()
            print(
                f"[INFO] [SEARCH] Indexed {stats['players']} players "
                f"({stats['listEntries']} list entries) in "
                f"{time.perf_counter() - began:.1f} s"
            )
        else:
            await self._apply_snapshot(players, started)

        self._changes = {
            key: change
            for key, change in self._changes.items()
            if change.generation > started
        }

    async def _apply_snapshot(self, players: dict[str, str | None], started: int):
        index = self._index
        snapshot_keys = {normalize_tag(tag) for tag in players}
        stale = [
            tag for tag, _ in index.items() if normalize_tag(tag) not in snapshot_keys
        ]
        updated = removed = 0

        for i, (tag, name) in enumerate(players.items()):
            if i and i % _DIFF_CHUNK == 0:
                await asyncio.sleep(0)
            # Checked right before applying: the loop may have run API
            # changes during the sleep.
            if index.get(tag) != (name or "") and not self._changed_since(tag, started):
                index.upsert(tag, name)
                updated += 1

        for i, tag in enumerate(stale):
            if i and i % _DIFF_CHUNK == 0:
                await asyncio.sleep(0)
            if not self._changed_since(tag, started) and index.remove(tag):
                removed += 1

        if updated or removed:
            print(
                f"[INFO] [SEARCH] Refresh applied {updated} new or renamed and "
                f"{removed} removed players"
            )

    async def _refresh_loop(self) -> None:
        while True:
            await asyncio.sleep(
                self._refresh_interval_s if self.ready else self._retry_s
            )
            try:
                await self.refresh()
            except Exception as e:
                print(f"[WARNING] [SEARCH] Index refresh failed: {e}")
