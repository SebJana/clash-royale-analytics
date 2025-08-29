from datetime import datetime, date, time, timedelta, timezone as tz_utc
from typing import Optional, Iterable
from zoneinfo import ZoneInfo


def match_tag_before_datetime_stage(player_tag: str, before_datetime: datetime):
    """
    Build a MongoDB $match stage that filters battles for a given player tag
    that happened before a given datetime

    Args:
        player_tag (str): Player tag (e.g., "#YYRJQY28") to match against `referencePlayerTag`.
        before_datetime (datetime.datetime): Beginning of lookup datetime (inclusive).

    Returns:
        dict: An aggregation stage of the form:
              {
                "$match": {
                    "referencePlayerTag": <player_tag>,
                    "battleTime": {"$lt": <end_datetime>}
                }
              }

    Notes: This function is a pure builder and does not execute any database operation
    """

    return {
        # Match the relevant files for the player and the time frame
        "$match": {
            "referencePlayerTag": player_tag,
            "battleTime": {"$lt": before_datetime},
        }
    }


def match_tag_date_mode_range_stage(
    player_tag: str,
    start_date: date,
    end_date: date,
    game_modes: Optional[Iterable[str]] = None,
    timezone: str = "UTC",
):
    """
    Build a MongoDB $match stage that filters battles for a given player tag
    within a full-day date window based on the given game modes.

    The window spans from `start_date` at 00:00:00 (inclusive) to
    `end_date + 1 day` at 00:00:00 (exclusive).

    Args:
        player_tag (str): Player tag (e.g., "#YYRJQY28") to match against `referencePlayerTag`.
        start_date (datetime.date): First day (inclusive).
        end_date (datetime.date): Last day (inclusive).
        game_modes: Optional iterable of game mode names; if provided and non-empty,
                    the match includes {"gameMode": {"$in": <game_modes>}}.
        timezone: Timezone into which the start_date and end_date will be transformed (default: UTC)


    Returns:
        dict: An aggregation stage of the form:
              {
                "$match": {
                  "referencePlayerTag": <player_tag>,
                  "battleTime": { "$gte": <start_dt>, "$lt": <end_dt_plus_1> },
                  "gameMode": {"$in": <game_modes>} (if game modes isn't empty)

                }
              }

    Notes: This function is a pure builder and does not execute any database operation
    """

    # Check if the given timezone exists and is valid
    try:
        tz = ZoneInfo(timezone)
    except Exception as e:
        raise ValueError(f"Invalid timezone: {timezone}") from e

    # Turn start/end date into requested timezone dates
    start_local = datetime.combine(start_date, time(0, 0), tzinfo=tz)
    end_local = datetime.combine(end_date + timedelta(days=1), time(0, 0), tzinfo=tz)

    # Convert to UTC for lookup in database
    start_utc = start_local.astimezone(tz_utc.utc)
    end_utc = end_local.astimezone(tz_utc.utc)

    match = {
        "referencePlayerTag": player_tag,
        "battleTime": {"$gte": start_utc, "$lt": end_utc},
    }

    # Only add the mode filter if provided and non-empty
    if game_modes:
        match["gameMode"] = {"$in": list(game_modes)}

    return {"$match": match}


def extract_deck_cards_stage(player_tag: str):
    """
    Build a MongoDB `$addFields` stage that extracts the given player's deck cards
    into a normalized `deckCards` array.

    For the team member with `tag == player_tag`, this stage pulls their `cards`
    array and maps each entry to the following schema:
      - `id` (card id; may be absent in some logs)
      - `name` (defaults to "UNKNOWN" if missing)
      - `level` (defaults to 1 if missing)
      - `evolutionLevel` (integer, defaults to 0 if missing, which is the default for non-evolution cards)

    Missing values are handled via `$ifNull`; `evolutionLevel` is cast to an int.

    Args:
        player_tag (str): The player tag used to select the team member whose
            cards should be extracted.

    Returns:
        dict: An aggregation pipeline stage:
              `{ "$addFields": { "deckCards": <mapped array> } }`,
              suitable for insertion into a larger pipeline.

    Notes: This function is a pure builder and does not execute any database operation
    """

    # Extract the cards from the decks for the given player including evolution data
    return {
        "$addFields": {
            "deckCards": {
                "$map": {
                    "input": {
                        "$ifNull": [
                            {
                                "$getField": {
                                    "field": "cards",
                                    "input": {
                                        "$first": {
                                            "$filter": {
                                                "input": "$team",
                                                "as": "m",
                                                "cond": {
                                                    "$eq": ["$$m.tag", player_tag]
                                                },
                                            }
                                        }
                                    },
                                }
                            },
                            [],
                        ]
                    },
                    "as": "c",
                    "in": {
                        "id": "$$c.id",
                        "name": {"$ifNull": ["$$c.name", "UNKNOWN"]},
                        "level": {"$ifNull": ["$$c.level", 1]},
                        "evolutionLevel": {
                            "$toInt": {"$ifNull": ["$$c.evolutionLevel", 0]}
                        },
                    },
                }
            }
        }
    }
