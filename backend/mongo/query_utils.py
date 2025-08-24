from datetime import datetime, timedelta

def match_tag_date_range_stage(player_tag: str, start_date, end_date):
    """
    Build a MongoDB $match stage that filters battles for a given player tag
    within a full-day date window.

    The window spans from `start_date` at 00:00:00 (inclusive) to
    `end_date + 1 day` at 00:00:00 (exclusive).

    Args:
        player_tag (str): Player tag (e.g., "YYRJQY28") to match against `referencePlayerTag`.
        start_date (datetime.date): First day (inclusive).
        end_date (datetime.date): Last day (inclusive).

    Returns:
        dict: An aggregation stage of the form:
              {
                "$match": {
                  "referencePlayerTag": <player_tag>,
                  "battleTime": { "$gte": <start_dt>, "$lt": <end_dt_plus_1> }
                }
              }

    Notes: This function is a pure builder and does not execute any database operation
    """
    
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt   = datetime.combine(end_date, datetime.min.time()) + timedelta(days=1)

    return {
        # Match the relevant files for the player and the time frame
        "$match": {
            "referencePlayerTag": player_tag,
            "battleTime": {"$gte": start_dt, "$lt": end_dt}
        }
    } 


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
                            {"$getField": {
                                "field": "cards",
                                "input": {
                                    "$first": {
                                        "$filter": {
                                            "input": "$team",
                                            "as": "m",
                                            "cond": {"$eq": ["$$m.tag", player_tag]}
                                        }
                                    }
                                }
                            }},
                            []
                        ]
                    },
                    "as": "c",
                    "in": {
                        "id": "$$c.id",
                        "name": {"$ifNull": ["$$c.name", "UNKNOWN"]},
                        "level": {"$ifNull": ["$$c.level", 1]},
                        "evolutionLevel": {"$toInt": {"$ifNull": ["$$c.evolutionLevel", 0]}},
                    }
                }
            }
        }
    }