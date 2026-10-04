"""In-memory search over tracked player names and tags.

Guarantees:
- Every true match is ranked before the result is cut to the limit. No
  cheaper first pass can drop a better match.
- The ranking is a total order, so the same players and query always give
  the same results, whatever order the players were added in.
- upsert and remove apply before they return, so a new player is searchable
  as soon as the add route has stored it.

Every trigram, and every one or two character prefix, maps to the players
containing it, pre-sorted by how a query of exactly that text would rank
them. Chinese, Japanese and Korean pieces of one or two characters are
listed from every position too, since there a single character is already
a word. A query up to three characters is the start of one list. A longer
query only checks the players in the shortest list among its trigrams: a
name without one of them cannot contain the query.

Not thread-safe. All mutations and searches run on the event loop; only a
fresh index is built in a worker thread.

Why in memory instead of SQLite FTS5 or Postgres pg_trgm?
Measured on synthetic names, where a common trigram like "roy" sits in
about 5% of all names, all with this ranking (desktop CPU):

    per search, 50k players     this: 0.005-0.15 ms
                                SQLite FTS5: 0.1-8 ms
                                Postgres: 0.1-4 ms + ~1.5 ms round trip
                                plain Python scan: 0.3-5 ms
    per search, 250k players    this: 0.005-0.85 ms
                                SQLite: 0.1-34 ms, Postgres: 0.1-18 ms
    insert one player           0.14 ms (50k), 0.18 ms (250k)
    memory                      ~18 MB (50k), ~82 MB (250k)
    full build                  ~2-3 s (50k), ~12-15 s (250k)

The databases are slowest on exactly the common case of autocomplete: a
short query matching thousands of names, which they rank row by row on every
request. Here that ranking is done once, ahead of time, so the query reads
the first `limit` entries of a list. Longer queries only check the shortest
trigram list. There is no network hop, query planner or second store to
keep in sync.

The design targets tens to a few hundred thousand tracked players. At that
scale a dedicated database or search engine buys nothing but cost: another
container to run and monitor, a network hop on every keystroke, another
dependency and driver, and a second copy of the players to keep in sync
with Mongo. This index lives in the API process, needs only the standard
library, and stays fast up to roughly 500k-1M players. Far beyond that,
memory, build time and long queries outgrow a single process, and a search
service with change-based sync becomes the better fit.

Ranking: Every match gets a sort key, smaller is better, and a search returns
the first `limit` keys over all matches:

    (tier, position, key length, key, tag)

    tier         kind of match, best first for a plain name query: exact tag,
                 exact name, name prefix, word start inside the name, anywhere
                 else in the name, tag prefix, anywhere else in the tag. A
                 query with a digit moves tag prefixes up to third; a query
                 starting with "#" puts every tag match first. An existing
                 full tag is pinned first in every mode.
    position     where the match starts; earlier is better.
    key length   shorter keys are closer to what was typed.
    key, tag     alphabetical, then the unique tag, so equal names still get
                 a fixed order.

For "roy" that gives: Roy (exact name), Royal King (prefix), TheRoyal (word
start at 3), SuperRoy (word start at 5), xxroyxx (inside, at 2), Ployroyd
(inside, at 3). Word starts come from normalize.normalize_name.

Size: A key of length n is listed under at most 2 prefixes and n - 2
trigrams, so at most n lists; a Chinese, Japanese or Korean key adds up to
2n - 1 one and two character pieces. Each list entry is a 4 byte slot number:

    entries per player   <= len(name key) + len(tag key)  (+ dense pieces)
    list memory          ~= 4 bytes x entries per player x players

Name keys have a median length of 7 and tags 8-9 characters, so about 16
entries per player. Measured on 4,248 tracked players: 72,501 entries (17
per player), built in 0.4 s. At 50k players that is ~850k entries and
~3.4 MB of lists; the per-player strings and dicts take most of the rest.

The build is the slow part: every one of those entries is sorted in Python.
It runs once at startup in a thread, and every later change is an
incremental upsert or remove.
"""

import heapq
from array import array
from bisect import bisect_left
from collections import defaultdict
from collections.abc import Callable, Iterable, Iterator
from typing import NamedTuple

from .normalize import is_dense, normalize_name, normalize_tag, parse_query

# Queries shorter than a trigram only match at the start of a name or tag.
# Common letter pairs like "ka" sit inside a large share of all names, so
# matching them anywhere would mostly return noise. Chinese, Japanese and
# Korean queries are the exception (see normalize.is_dense).
GRAM = 3

# Match tiers, the first part of the sort key (see "Ranking" in the module
# docstring). Best first for a plain name query; the orders below move the
# tag tiers up for tag-like queries.
EXACT_TAG = 0
EXACT_NAME = 1
NAME_PREFIX = 2
NAME_WORD = 3
NAME_INFIX = 4
TAG_PREFIX = 5
TAG_INFIX = 6

MATCH_TYPES = (
    "exactTag",
    "exactName",
    "namePrefix",
    "nameWord",
    "nameInfix",
    "tagPrefix",
    "tagInfix",
)

# Result position of each tier, indexed by tier. Every order keeps the name
# tiers and the tag tiers in their own relative order, so lists pre-sorted
# by tier stay sorted in any order and merge without re-sorting.
_NAME_FIRST = (0, 1, 2, 3, 4, 5, 6)
# A query with a digit is likely a tag: tag prefixes move above name prefixes.
_TAG_PREFIX_FIRST = (0, 1, 3, 4, 5, 2, 6)
# A query starting with "#" means a tag: every tag match comes first.
_TAGS_FIRST = (0, 3, 4, 5, 6, 1, 2)

# Bits for a player's tie-break rank in a packed build sort key. Enough for
# 4 billion players; the slot arrays are 32 bit anyway.
_RANK_BITS = 32


class _Entry(NamedTuple):
    tag: str
    name: str
    name_key: str
    name_starts: int
    tag_key: str


class SearchResult(NamedTuple):
    """One ranked search result. match is one of MATCH_TYPES."""

    tag: str
    name: str
    match: str


def _name_match(key: str, starts: int, query: str) -> tuple[int, int] | None:
    """Return the tier and position of query in a name key, None without a match.

    A match at a word start beats an earlier match inside a word, so "roy"
    in "xroySuperRoy" counts as a word match at position 9.
    """

    pos = key.find(query)
    if pos < 0:
        return None
    if pos == 0:
        return (EXACT_NAME if len(key) == len(query) else NAME_PREFIX), 0
    if len(query) < GRAM and not is_dense(query):
        return None
    # The first occurrence may sit inside a word while a later one starts a
    # word; walk the occurrences until one does.
    word = pos
    while word >= 0:
        if starts >> word & 1:
            return NAME_WORD, word
        word = key.find(query, word + 1)
    return NAME_INFIX, pos


def _tag_match(key: str, query: str) -> tuple[int, int] | None:
    """Return the tier and position of query in a tag key, None without a match."""

    pos = key.find(query)
    if pos < 0:
        return None
    if pos == 0:
        return TAG_PREFIX, 0
    if len(query) < GRAM:
        return None
    return TAG_INFIX, pos


def _groups(key: str) -> tuple[set[str], set[str], set[str]]:
    """Return the prefixes, trigrams and dense pieces a key is listed under.

    Dense pieces are the Chinese, Japanese and Korean runs of one or two
    characters at any position. ASCII keys, most of them, have none.
    """

    if not key:
        return set(), set(), set()
    prefixes = {key[:1], key[:2]}
    grams = {key[i : i + GRAM] for i in range(len(key) - 2)}
    dense = set()
    if not key.isascii():
        dense = {
            key[i : i + size]
            for size in (1, 2)
            for i in range(len(key) - size + 1)
            if is_dense(key[i : i + size])
        }
    return prefixes, grams, dense


class _Side:
    """The prefix, trigram and dense lists of one field (names or tags)."""

    def __init__(self, sort_key: Callable[[int, str], tuple]):
        # Each list holds slot numbers as array("I"): raw 4 byte unsigned
        # ints in one block. A Python list would hold an 8 byte pointer to a
        # ~28 byte int object per entry, about 36 bytes instead of 4. "I" is
        # 4 bytes on every common platform ("L" is 8 on Linux), which caps
        # slots at 2**32 - 1. The price: inserting or deleting in the middle
        # shifts the rest of the array, which is most of what upsert and
        # remove spend their time on in large lists.
        self.prefixes: dict[str, array] = {}
        self.grams: dict[str, array] = {}
        self.dense: dict[str, array] = {}
        # (slot, query) -> (tier, position, key length, key, tag key), the
        # order every list is kept in.
        self.sort_key = sort_key

    @property
    def all_lists(self) -> tuple[dict[str, array], ...]:
        """The list dicts in the order _groups returns their members."""

        return self.prefixes, self.grams, self.dense

    def link(self, slot: int, key: str) -> None:
        for lists, members in zip(self.all_lists, _groups(key)):
            for group in members:
                slots = lists.get(group)
                if slots is None:
                    lists[group] = array("I", [slot])
                    continue
                # Binary search by the sort key the list is ordered by. The
                # list stores slots, so the key is computed per probed slot;
                # g=group binds this loop's group into the lambda.
                at = bisect_left(
                    slots,
                    self.sort_key(slot, group),
                    key=lambda s, g=group: self.sort_key(s, g),
                )
                slots.insert(at, slot)

    def unlink(self, slot: int, key: str) -> None:
        """Remove a slot. Its entry HAS to still hold the key it was linked with."""

        for lists, members in zip(self.all_lists, _groups(key)):
            for group in members:
                slots = lists[group]
                # Sort keys end with the unique tag, so no two slots share
                # one and the search lands exactly on this slot.
                at = bisect_left(
                    slots,
                    self.sort_key(slot, group),
                    key=lambda s, g=group: self.sort_key(s, g),
                )
                # Only possible if a list was corrupted or the entry changed
                # before unlinking; failing loudly beats a silent stale hit.
                if at >= len(slots) or slots[at] != slot:
                    raise RuntimeError(f"Search list {group!r} lost slot {slot}")
                del slots[at]
                if not slots:
                    del lists[group]

    def _short_query_lists(self, query: str) -> dict[str, array]:
        """The lists whose entry for query already holds every match, in order."""

        if len(query) == GRAM:
            return self.grams
        # Short Chinese, Japanese and Korean queries match anywhere.
        return self.dense if is_dense(query) else self.prefixes

    def matches(self, query: str, order: tuple, limit: int) -> Iterator[tuple]:
        """Yield the matches for query, best first, as merge-ready tuples.

        Only the start of a pre-sorted list is read for queries up to GRAM
        long. Longer queries check every candidate, then keep the best
        `limit`: no player beyond a side's own top `limit` can reach the
        overall top `limit`.
        """

        # Yielded as (order position, position, key length, key, tag key,
        # tier, slot). heapq.merge compares them up to the tag key, which is
        # unique, so tier and slot only ride along: the tier names the match
        # type in the result, the slot finds the player.
        if len(query) <= GRAM:
            for slot in self._short_query_lists(query).get(query, ()):
                tier, pos, *rest = self.sort_key(slot, query)
                yield (order[tier], pos, *rest, tier, slot)
            return

        # Every match contains every trigram of the query, so any one list is
        # a complete candidate set; the shortest is the cheapest to check. A
        # trigram no key has means no match at all.
        candidates = None
        for i in range(len(query) - 2):
            slots = self.grams.get(query[i : i + GRAM])
            if slots is None:
                return
            if candidates is None or len(slots) < len(candidates):
                candidates = slots
        found = []
        for slot in candidates:
            # None when the trigrams occur, but not as one run ("aab...aaa"
            # holds both trigrams of "aaab" without containing it).
            rank = self.sort_key(slot, query)
            if rank is not None:
                tier, pos, *rest = rank
                found.append((order[tier], pos, *rest, tier, slot))
        yield from heapq.nsmallest(limit, found)


class PlayerSearchIndex:
    """Ranked substring search over player names and tags. See the module docstring."""

    def __init__(self):
        # slot -> player. A slot is just a player's position here, 0 to N-1
        # after a build, and the number every list stores. It carries no
        # meaning; the order inside a list comes from the sort key. A removed
        # player's slot goes to _free and the next new player reuses it.
        self._entries: list[_Entry | None] = []
        self._free: list[int] = []
        # tag key -> slot, for exact tags, upsert and remove.
        self._by_tag: dict[str, int] = {}
        self._names = _Side(self._name_sort_key)
        self._tags = _Side(self._tag_sort_key)

    def _name_sort_key(self, slot: int, query: str) -> tuple | None:
        e = self._entries[slot]
        match = _name_match(e.name_key, e.name_starts, query)
        if match is None:
            return None
        return (*match, len(e.name_key), e.name_key, e.tag_key)

    def _tag_sort_key(self, slot: int, query: str) -> tuple | None:
        e = self._entries[slot]
        match = _tag_match(e.tag_key, query)
        if match is None:
            return None
        # The tag key fills both the key and the tie-break place, so name and
        # tag sort keys have the same shape and merge into one ranking.
        return (*match, len(e.tag_key), e.tag_key, e.tag_key)

    @staticmethod
    def _entry(tag: str, name: str | None, tag_key: str) -> _Entry:
        name = name or ""
        name_key, starts = normalize_name(name)
        return _Entry(tag, name, name_key, starts, tag_key)

    @classmethod
    def build(cls, players: Iterable[tuple[str, str | None]]) -> "PlayerSearchIndex":
        """Build an index from (tag, name) pairs in one pass.

        Sorting every list once is much faster than inserting players one by
        one. Each list member is packed into one int (tier, position, rank by
        key length, key and tag), so the sorts compare ints instead of tuples
        and give exactly the order upsert keeps.

        Args:
            players (Iterable[tuple[str, str | None]]): Tags and names. A
                repeated tag keeps its last name.

        Returns:
            PlayerSearchIndex: The populated index.
        """

        index = cls()
        for tag, name in players:
            tag_key = normalize_tag(tag)
            if not tag_key:
                continue
            slot = index._by_tag.get(tag_key)
            if slot is None:
                slot = len(index._entries)
                index._entries.append(None)
                index._by_tag[tag_key] = slot
            index._entries[slot] = cls._entry(tag, name, tag_key)

        # A player's position in these orders is their tie-break rank: one
        # small int that sorts like (key length, key, tag), the last three
        # parts of every sort key, so _fill can pack whole keys into ints.
        entries = index._entries
        by_name = sorted(
            range(len(entries)),
            key=lambda s: (
                len(entries[s].name_key),
                entries[s].name_key,
                entries[s].tag_key,
            ),
        )
        by_tag = sorted(
            range(len(entries)),
            key=lambda s: (len(entries[s].tag_key), entries[s].tag_key),
        )
        index._fill(index._names, by_name, lambda e: e.name_key, index._name_sort_key)
        index._fill(index._tags, by_tag, lambda e: e.tag_key, index._tag_sort_key)
        return index

    def _fill(
        self,
        side: _Side,
        slot_by_rank: list[int],
        key_of: Callable[[_Entry], str],
        sort_key: Callable[[int, str], tuple],
    ) -> None:
        mask = (1 << _RANK_BITS) - 1
        packed = tuple(defaultdict(list) for _ in side.all_lists)
        for rank, slot in enumerate(slot_by_rank):
            key = key_of(self._entries[slot])
            for lists, members in zip(packed, _groups(key)):
                for group in members:
                    tier, pos = sort_key(slot, group)[:2]
                    # One int per entry, bits from high to low: tier, match
                    # position (32 bits), tie-break rank (32 bits). Comparing
                    # these ints compares the full sort keys.
                    lists[group].append((tier << 32 | pos) << _RANK_BITS | rank)
        # Sorted ints back to slots: the low bits are the rank, and
        # slot_by_rank turns a rank into its slot.
        for target, lists in zip(side.all_lists, packed):
            for group, values in lists.items():
                values.sort()
                target[group] = array("I", (slot_by_rank[v & mask] for v in values))

    def upsert(self, tag: str, name: str | None) -> bool:
        """Add a player or update their name.

        Args:
            tag (str): The player tag, e.g. "#YYRJQY28".
            name (str | None): The player name; None indexes the tag only.

        Returns:
            bool: False when the player was already indexed with this exact
                tag and name, True otherwise.

        Raises:
            ValueError: If the tag is empty after normalization.
        """

        tag_key = normalize_tag(tag)
        if not tag_key:
            raise ValueError(f"Cannot index an empty tag: {tag!r}")
        slot = self._by_tag.get(tag_key)
        if slot is not None:
            old = self._entries[slot]
            if old.tag == tag and old.name == (name or ""):
                return False
            # Unlinked while the old entry is still in place: the lists find
            # a slot by its sort key, which comes from the entry.
            self._names.unlink(slot, old.name_key)
            self._tags.unlink(slot, old.tag_key)
        elif self._free:
            slot = self._free.pop()
        else:
            slot = len(self._entries)
            self._entries.append(None)
        self._entries[slot] = self._entry(tag, name, tag_key)
        self._by_tag[tag_key] = slot
        self._names.link(slot, self._entries[slot].name_key)
        self._tags.link(slot, tag_key)
        return True

    def remove(self, tag: str) -> bool:
        """Remove a player. Returns False if the tag was not indexed."""

        slot = self._by_tag.pop(normalize_tag(tag), None)
        if slot is None:
            return False
        entry = self._entries[slot]
        self._names.unlink(slot, entry.name_key)
        self._tags.unlink(slot, entry.tag_key)
        self._entries[slot] = None
        self._free.append(slot)
        return True

    def search(self, query: str, limit: int) -> list[SearchResult]:
        """Return the best `limit` players for a query, best first.

        Names and tags are both searched and an existing full tag is pinned
        first. A leading "#" ranks every tag match above every name match.

        Args:
            query (str): The query as typed.
            limit (int): Maximum number of results.

        Returns:
            list[SearchResult]: Ranked results, each player at most once.
        """

        parsed = parse_query(query)
        picked: list[tuple[int, int]] = []
        seen: set[int] = set()

        exact = self._by_tag.get(parsed.tag) if parsed.tag else None
        if exact is not None:
            picked.append((exact, EXACT_TAG))
            seen.add(exact)

        if parsed.tags_first:
            order = _TAGS_FIRST
        elif parsed.tag_prefix_first:
            order = _TAG_PREFIX_FIRST
        else:
            order = _NAME_FIRST
        # Both sides yield best first in the same order, so merging them gives
        # one ranking without sorting. A player matching by name and by tag
        # comes up twice; the first, better match wins and the second is
        # skipped. The sides are lazy, so only about `limit` entries are read.
        sides = []
        if parsed.name:
            sides.append(self._names.matches(parsed.name, order, limit))
        if parsed.tag:
            sides.append(self._tags.matches(parsed.tag, order, limit))
        for *_, tier, slot in heapq.merge(*sides):
            if len(picked) >= limit:
                break
            if slot not in seen:
                seen.add(slot)
                picked.append((slot, tier))
        return self._results(picked[:limit])

    def _results(self, picked: list[tuple[int, int]]) -> list[SearchResult]:
        return [
            SearchResult(
                self._entries[slot].tag, self._entries[slot].name, MATCH_TYPES[tier]
            )
            for slot, tier in picked
        ]

    def get(self, tag: str) -> str | None:
        """Return the indexed name of a tag, None if the tag is not indexed."""

        slot = self._by_tag.get(normalize_tag(tag))
        return None if slot is None else self._entries[slot].name

    def items(self) -> Iterator[tuple[str, str]]:
        """Yield every indexed (tag, name) pair."""

        for entry in self._entries:
            if entry is not None:
                yield entry.tag, entry.name

    def __len__(self) -> int:
        return len(self._by_tag)

    def stats(self) -> dict[str, int]:
        """Return the index size for logging."""

        sides = (*self._names.all_lists, *self._tags.all_lists)
        return {
            "players": len(self),
            "nameTrigrams": len(self._names.grams),
            "tagTrigrams": len(self._tags.grams),
            "listEntries": sum(len(v) for lists in sides for v in lists.values()),
        }
