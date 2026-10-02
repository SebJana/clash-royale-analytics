from datetime import datetime, timezone
from pymongo import ReturnDocument
from .connection import MongoConn
from .validation_utils import ensure_connected


async def insert_tracked_player(
    conn: MongoConn, player_tag: str, player_name: str = "Player"
) -> str:
    """
    Insert (or reactivate) a player in the `players` collection.

    - If the player doesn't exist: create with active=True.
    - If the player exists: set active=True again (reactivate).

    Args:
        conn (MongoConn): Active MongoDB connection instance.
        player_tag (str): The unique tag of the player (e.g., "#YYRJQY28").
        player_name (str): The name to set for the player (default: "Player").

    Returns:
        str: "created", "reactivated", or "already_active"
    """
    try:
        await ensure_connected(conn)
        now = datetime.now().strftime("%Y-%m-%d %H-%M-%S")

        # Try to reactivate if it exists but is inactive
        res = await conn.db.players.update_one(
            {"playerTag": player_tag, "active": False},
            # Pipeline update, so the gap can be built from the stored
            # deactivatedAt in the same atomic write.
            [
                {
                    "$set": {
                        "active": True,
                        "reactivatedAt": now,
                        "updatedAt": now,
                        "consecutiveFailures": 0,
                        "consecutiveNotFound": 0,
                        # Battles played while untracked are only recovered
                        # if they still fit into the battle log, so every
                        # untracked period is kept for the player page.
                        "trackingGaps": {
                            "$concatArrays": [
                                {"$ifNull": ["$trackingGaps", []]},
                                [{"from": "$deactivatedAt", "to": now}],
                            ]
                        },
                    }
                },
                # A player deactivated after repeated 404s exists again, so
                # its old not-found streak must not count towards a new one.
                {"$unset": ["deactivatedReason", "firstNotFoundAt"]},
            ],
            upsert=False,
        )
        if res.matched_count == 1:
            return "reactivated"

        # If not matched above, upsert (create if missing, otherwise just ensure active)
        res = await conn.db.players.update_one(
            {"playerTag": player_tag},
            {
                "$set": {"playerTag": player_tag, "active": True, "updatedAt": now},
                "$setOnInsert": {
                    "insertedAt": now,
                    "playerName": player_name,
                    "syncVersion": 0,
                },
            },
            upsert=True,
        )

        if res.upserted_id is not None:
            return "created"

        return "already_tracked"

    except Exception as e:
        print(f"[DB] [ERROR] during insert/reactivate for player: {player_tag}", e)
        raise


async def set_player_name(conn: MongoConn, player_tag: str, player_name: str):
    """
    Updates the name of an existing player (by tag) in the players collection.
    It does not insert a new document if the player does not exist (upsert=False).

    Args:
        conn (MongoConn): Active MongoDB connection instance.
        player_tag (str): The unique tag of the player (e.g., "#YYRJQY28").
        player_name (str): The new name to set for the player.

    Raises:
        Exception: Any exception that occurs during the database update operation.
    """

    try:
        await ensure_connected(conn)

        # Set the name for the player with the specified tag
        res = await conn.db.players.update_one(
            {"playerTag": player_tag},
            {"$set": {"playerName": player_name}},
            upsert=False,
        )

        if res.matched_count == 0:
            print(
                f"[DB] [WARNING] player {player_tag} was not found in collection and couldn't set player name."
            )

    except Exception as e:
        print(f"[DB] [ERROR] during name setting for player: {player_tag}", e)
        raise


async def deactivate_tracked_player(
    conn: MongoConn, player_tag, reason: str | None = None
) -> int:
    """
    Deactivates a player that is being tracked into the players collection.

    Args:
        conn (MongoConn): Active connection to the mongo database
        player_tag (str): The player tag starting with '#' (e.g., "#YYRJQY28")
        reason (str | None): Stored as deactivatedReason when the system, not
            a user, untracks the player (e.g. "not_found")

    Returns:
        int: The amount of affected players by the update

    Raises:
        Exception: If the update of the player fails
    """

    try:
        await ensure_connected(conn)
        current_time = datetime.now().strftime("%Y-%m-%d %H-%M-%S")

        fields = {"active": False, "deactivatedAt": current_time}
        if reason:
            fields["deactivatedReason"] = reason

        res = await conn.db.players.update_one(
            {"playerTag": player_tag, "active": True}, {"$set": fields}
        )

        # Return the amount of players updated
        return res.matched_count

    except Exception as e:
        print(f"[DB] [ERROR] during update: {e}")
        raise


async def record_battle_sync(
    conn: MongoConn,
    player_tag: str,
    newest_battle_time: datetime | None,
    player_name: str | None,
    inserted_count: int,
    interval_s: float | None = None,
):
    """
    Stores the outcome of a successful battle sync on the player document.

    syncVersion is only incremented when new battles were inserted. Cached
    statistics of a player without new battles therefore stay valid.

    Args:
        conn (MongoConn): Active MongoDB connection instance.
        player_tag (str): The unique tag of the player (e.g., "#YYRJQY28").
        newest_battle_time (datetime | None): battleTime of the newest battle in
            the fetched battle log, None if the log was empty.
        player_name (str | None): Current player name, None to keep the stored one.
        inserted_count (int): Number of battles inserted by this sync.
        interval_s (float | None): Seconds until the player's next battle sync.
            Stored so the next interval can grow from it, and so a rebuilt
            schedule keeps the player's rhythm.

    Raises:
        Exception: Any exception that occurs during the database update operation.
    """

    try:
        await ensure_connected(conn)

        update = {
            "$set": {
                "lastBattlesSyncAt": datetime.now(timezone.utc),
                "consecutiveFailures": 0,
                "consecutiveNotFound": 0,
            },
            "$unset": {"firstNotFoundAt": ""},
        }
        if player_name:
            update["$set"]["playerName"] = player_name
        if interval_s is not None:
            update["$set"]["syncIntervalS"] = interval_s
        if newest_battle_time is not None:
            # $max keeps the watermark from moving backwards if two syncs of
            # the same player overlap after an expired claim.
            update["$max"] = {"lastBattleTime": newest_battle_time}
        if inserted_count > 0:
            update["$inc"] = {"syncVersion": 1}

        await conn.db.players.update_one(
            {"playerTag": player_tag}, update, upsert=False
        )

    except Exception as e:
        print(f"[DB] [ERROR] recording the battle sync of {player_tag}", e)
        raise


async def record_battle_sync_failure(
    conn: MongoConn, player_tag: str, not_found: bool = False
) -> dict:
    """
    Counts a failed battle sync on the player document.

    Args:
        conn (MongoConn): Active MongoDB connection instance.
        player_tag (str): The unique tag of the player (e.g., "#YYRJQY28").
        not_found (bool): The Clash Royale API answered 404 for the player.

    Returns:
        dict: consecutiveFailures, consecutiveNotFound and firstNotFoundAt after
            this failure (empty if the player doesn't exist)

    Raises:
        Exception: Any exception that occurs during the database update operation.
    """

    try:
        await ensure_connected(conn)
        now = datetime.now(timezone.utc)

        fields = {
            "consecutiveFailures": {
                "$add": [{"$ifNull": ["$consecutiveFailures", 0]}, 1]
            },
        }
        if not_found:
            # Keep the first 404 of a streak, so deactivation can require the
            # player to be missing over a minimum time span.
            fields["consecutiveNotFound"] = {
                "$add": [{"$ifNull": ["$consecutiveNotFound", 0]}, 1]
            }
            fields["firstNotFoundAt"] = {"$ifNull": ["$firstNotFoundAt", now]}

        doc = await conn.db.players.find_one_and_update(
            {"playerTag": player_tag},
            [{"$set": fields}],
            projection={
                "_id": 0,
                "consecutiveFailures": 1,
                "consecutiveNotFound": 1,
                "firstNotFoundAt": 1,
            },
            return_document=ReturnDocument.AFTER,
        )
        return doc or {}

    except Exception as e:
        print(f"[DB] [ERROR] recording the failed sync of {player_tag}", e)
        raise


async def backfill_tracking_gaps(conn: MongoConn) -> int:
    """
    Adds trackingGaps to players stored before the field existed.

    Earlier versions only kept the last deactivatedAt and reactivatedAt, so at
    most the latest untracked period can be recovered: when the reactivation
    followed the deactivation. Only players without trackingGaps are touched,
    so this is safe to run on every start.

    Args:
        conn (MongoConn): Active MongoDB connection instance.

    Returns:
        int: Number of updated players

    Raises:
        Exception: Any exception that occurs during the update.
    """

    try:
        await ensure_connected(conn)

        both_present = {
            "$and": [
                {"$ne": [{"$type": "$deactivatedAt"}, "missing"]},
                {"$ne": [{"$type": "$reactivatedAt"}, "missing"]},
                # Both are "YYYY-MM-DD HH-MM-SS" strings, which sort by time
                {"$lte": ["$deactivatedAt", "$reactivatedAt"]},
            ]
        }
        res = await conn.db.players.update_many(
            {"trackingGaps": {"$exists": False}},
            [
                {
                    "$set": {
                        "trackingGaps": {
                            "$cond": [
                                both_present,
                                [{"from": "$deactivatedAt", "to": "$reactivatedAt"}],
                                [],
                            ]
                        }
                    }
                }
            ],
        )
        return res.modified_count

    except Exception as e:
        print("[DB] [ERROR] backfilling the tracking gaps", e)
        raise


async def backfill_player_sync_fields(conn: MongoConn) -> int:
    """
    Adds the per-player sync fields to players stored before they existed.

    Sets syncVersion to 0 and lastBattleTime to the newest stored battle of the
    player. Only players without syncVersion are touched, so this is safe to
    run on every start.

    Args:
        conn (MongoConn): Active MongoDB connection instance.

    Returns:
        int: Number of updated players

    Raises:
        Exception: Any exception that occurs during the lookup or update.
    """

    try:
        await ensure_connected(conn)

        updated = 0
        cursor = conn.db.players.find(
            {"syncVersion": {"$exists": False}}, {"_id": 0, "playerTag": 1}
        )
        async for doc in cursor:
            player_tag = doc["playerTag"]
            # Served by the unique (referencePlayerTag, battleTime) index
            newest = await conn.db.battles.find_one(
                {"referencePlayerTag": player_tag},
                {"_id": 0, "battleTime": 1},
                sort=[("battleTime", -1)],
            )
            fields = {"syncVersion": 0}
            if newest:
                fields["lastBattleTime"] = newest["battleTime"]
            res = await conn.db.players.update_one(
                {"playerTag": player_tag, "syncVersion": {"$exists": False}},
                {"$set": fields},
            )
            updated += res.modified_count
        return updated

    except Exception as e:
        print("[DB] [ERROR] backfilling the player sync fields", e)
        raise
