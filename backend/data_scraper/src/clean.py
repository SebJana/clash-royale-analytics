from datetime import datetime, timedelta
import copy


def validate_battle_log_structure(battle_logs):
    """
    Validates the API response if it is in the correct form and syntax.

    Args:
        battle_logs: The response from the Clash Royale API

    Returns:
        bool: True if the response is valid, False otherwise
    """

    # Check if battle_logs is None or empty
    if not battle_logs:
        return False

    # Check if it's a list (expected format)
    if not isinstance(battle_logs, list):
        return False

    # Check if the list is empty
    if len(battle_logs) == 0:
        return False

    # Validate first battle log structure
    first_battle = battle_logs[0]

    # Check if it's a dictionary
    if not isinstance(first_battle, dict):
        print(f"[VALIDATION] Expected battle to be dict, got {type(first_battle)}")
        return False

    return True


def validate_battle_log_content(battle_logs):
    """
    Validates the API response to ensure it contains valid battle log data.

    Args:
        battle_logs: The response from the Clash Royale API

    Returns:
        bool: True if the response is valid, False otherwise
    """

    # Validate first battle log content
    first_battle = battle_logs[0]

    # Check for required fields
    required_fields = ["battleTime", "team", "opponent", "arena", "gameMode"]
    for field in required_fields:
        if field not in first_battle:
            print(f"[VALIDATION] Missing required field: {field}")
            return False

    # Validate team and opponent structure
    team = first_battle.get("team")
    opponent = first_battle.get("opponent")

    if not isinstance(team, list) or not isinstance(opponent, list):
        print("[VALIDATION] Team or opponent is not a list")
        return False

    if len(team) == 0 or len(opponent) == 0:
        print("[VALIDATION] Team or opponent list is empty")
        return False

    # Check if team and opponent players have required fields
    for player in team + opponent:
        if not isinstance(player, dict):
            print("[VALIDATION] Player is not a dictionary")
            return False

        if "cards" not in player:
            print("[VALIDATION] Player missing cards field")
            return False

        if not isinstance(player["cards"], list):
            print("[VALIDATION] Player cards is not a list")
            return False

    return True


def adjust_card_levels(cards):
    """
    Adjusts card levels from the old Clash Royale level system to the new level system.

    The old system had different max levels per rarity, while the new system
    normalizes all cards to level 14/15 with different starting levels per rarity.

    Args:
        cards (list): List of card dictionaries to adjust levels for
    """

    # Clash Royale changed the level system, but their API still returns the old
    # levels. Back then all cards started at level 1 and could be leveled up.
    # Maxed out: Level 13 for common cards, level 11 for rare cards, level 8 for epic cards, ...
    # Nowadays everything is capped at level 14 (15), and the different rarities
    # just start off at different starting levels:
    #   common: 1
    #   rare: 3
    #   epic: 6
    #   legendary: 9
    #   champion: 11

    rarity_level_offsets = {
        "common": 0,
        "rare": 2,
        "epic": 5,
        "legendary": 8,
        "champion": 10,
    }

    # Additionally the card level can be higher than the maxLevel specified for the card
    # Clash Royale introduced Level 15 for all cards, without changing the stat in the API response

    for card in cards:
        # Determine level and rarity and offset it to the new system
        old_card_level = card.get("level")
        rarity = card.get("rarity")
        new_level = old_card_level + rarity_level_offsets[rarity]

        # Save the new level as card level
        card["level"] = new_level


def remove_unnecessary_card_fields(cards):
    """
    Removes unnecessary fields from card objects to reduce storage size.

    Keeps essential fields like name and id for card identification while
    removing metadata that can be retrieved from other sources.

    Args:
        cards (list): List of card dictionaries to clean
    """

    # Remove fields that aren't necessary for storing
    # Keep name and id for each card, so that when id should ever change
    # the already stored data can still be connected to the card via the name
    keys_to_remove = [
        "maxLevel",
        "maxEvolutionLevel",
        "rarity",
        "starLevel",
        "elixirCost",
        "iconUrls",
        "used",  # Only a stat for a card when it's a duel
    ]

    for card in cards:
        for key in keys_to_remove:
            card.pop(key, None)


def determine_game_result(battle):
    """
    Determines the result of a battle based on crown counts.

    Compares the crown count between the reference player's team and opponents
    to determine if the battle was a victory, defeat, or draw.

    Args:
        battle (dict): Battle log dictionary containing team and opponent data

    Returns:
        str: "Victory", "Defeat", or "Draw"
    """

    # Default to zero as crown amount if it can't be found in the json
    own_crowns = battle.get("team")[0].get("crowns", 0)
    opponent_crowns = battle.get("opponent")[0].get("crowns", 0)

    # Check who won
    if own_crowns > opponent_crowns:
        return "Victory"

    if own_crowns < opponent_crowns:
        return "Defeat"

    # Upon same crown amount
    return "Draw"


def clean_battle_log_list(battle_logs, player_tag):
    """
    Processes and cleans a list of battle logs from the Clash Royale API.

    Adds metadata, converts timestamps, determines game results, and removes
    unnecessary fields to prepare the data for database storage.

    Args:
        battle_logs (list): List of raw battle log dictionaries from the API
        player_tag (str): The player tag to use as reference for the battles

    Returns:
        list: List of cleaned and processed battle log dictionaries
    """

    i = 0
    while i < len(battle_logs):
        battle = battle_logs[i]

        # Battle is a best of 3 duel, needs own extraction logic
        if battle.get("team") and battle["team"][0].get("rounds"):
            duel_battles = extract_duel_battles(battle)
            battle_logs.pop(i)  # Remove the current un-extracted duel battle log
            battle_logs[i:i] = (
                duel_battles  # Insert the extracted duel battles, they will be cleaned after
            )
            continue  # move to the next battle, which is the first battle of the duel

        # Add a reference player tag to each battle
        # Tag combined with time is unique identifier for each battle
        battle["referencePlayerTag"] = player_tag

        # Turn the date/time format into ISO time
        battle_time = battle.get("battleTime")  # e.g. "20250817T022935.000Z"
        # Parse to datetime
        battle_time = datetime.strptime(battle_time, "%Y%m%dT%H%M%S.000Z")
        battle["battleTime"] = battle_time

        # For each battle in the log format and clean it
        clean_battle(battle)

        # See if game ended in victory/defeat or draw
        battle["gameResult"] = determine_game_result(battle)

        # Remove the unnecessary stats from each battle
        keys_to_remove = [
            "deckSelection",
            "isHostedMatch",
            "leagueNumber",
            "isLadderTournament",
        ]

        for key in keys_to_remove:
            battle.pop(key, None)

        # Refactor Arena and GameMode (get rid of id)
        arena = battle.get("arena").get("name")
        battle["arena"] = arena

        game_mode = battle.get("gameMode").get("name")
        battle["gameMode"] = game_mode

        i += 1  # move to the next battle

    return battle_logs


def extract_duel_battles(battle):
    """
    Extracts individual battles from a best-of-3 duel battle log.

    Each duel in the Clash Royale API is represented as a single battle entry
    containing multiple "rounds". This function expands that combined entry into
    separate battle dictionaries, one per round, by copying the original structure,
    replacing the per-round values (cards, crowns, towers, elixir), and adjusting
    the battle timestamp to be unique for each round by a one second offset per round.

    Args:
        battle (dict): A raw duel battle log dictionary from the Clash Royale API.

    Returns:
        list: A list of battle dictionaries, one for each round of the duel.
    """

    extracted = []

    team_list = battle.get("team") or []
    opp_list = battle.get("opponent") or []

    # handle empty/odd cases
    team_player = team_list[0] if team_list else {}
    opp_player = opp_list[0] if opp_list else {}

    team_rounds = team_player.get("rounds") or []
    opp_rounds = opp_player.get("rounds") or []

    # iterate only over rounds that exist on both sides
    # should always be same amount
    for i in range(min(len(team_rounds), len(opp_rounds))):
        team = team_rounds[i]
        opp = opp_rounds[i]
        current_battle = copy.deepcopy(battle)

        # ensure lists exist and have at least one player
        if not current_battle.get("team"):
            current_battle["team"] = [{}]
        if not current_battle.get("opponent"):
            current_battle["opponent"] = [{}]

        # write per-round values onto player #0
        team0 = current_battle["team"][0]
        opp0 = current_battle["opponent"][0]

        # TEAM per-round
        team0["cards"] = team.get("cards")
        team0["crowns"] = team.get("crowns")
        team0["kingTowerHitPoints"] = team.get("kingTowerHitPoints")
        team0["princessTowersHitPoints"] = team.get("princessTowersHitPoints")
        team0["elixirLeaked"] = team.get("elixirLeaked")
        team0.pop("rounds")  # Remove the rounds list from the current battle

        # OPPONENT per-round
        opp0["cards"] = opp.get("cards")
        opp0["crowns"] = opp.get("crowns")
        opp0["kingTowerHitPoints"] = opp.get("kingTowerHitPoints")
        opp0["princessTowersHitPoints"] = opp.get("princessTowersHitPoints")
        opp0["elixirLeaked"] = opp.get("elixirLeaked")
        opp0.pop("rounds")  # Remove the rounds list from the current battle

        battle_time_str = current_battle.get("battleTime")
        dt = datetime.strptime(battle_time_str, "%Y%m%dT%H%M%S.000Z")

        # Shift by i seconds, so the position in the duel
        dt_shifted = dt + timedelta(seconds=i)
        current_battle["battleTime"] = dt_shifted.strftime("%Y%m%dT%H%M%S.000Z")

        # TODO (potentially) add unique match ID

        extracted.append(current_battle)

    return extracted


def clean_battle(battle):
    """
    Cleans individual battle data by processing player information.

    Removes unnecessary player fields, adjusts card levels, and cleans up
    card data for both team and opponent players in the battle.

    Args:
        battle (dict): Single battle log dictionary to clean
    """

    team = battle.get("team")
    opponent = battle.get("opponent")

    # Loop over every player in the battle: team player(s) and opponent player(s)
    for player in team + opponent:
        # Remove the clan for each player
        player.pop("clan", None)

        # Clean and adjust the players deck cards
        adjust_card_levels(player.get("cards"))
        remove_unnecessary_card_fields(player.get("cards"))

        # Clean and adjust the players support card(s) [Tower Troop]
        adjust_card_levels(player.get("supportCards"))
        remove_unnecessary_card_fields(player.get("supportCards"))

        player.pop("globalRank", None)


def get_player_name(battles, player_tag):
    """
    Extracts the player's name from the most recent battle log entry.

    Args:
        battles (list[dict]): List of battle dictionaries (newest first) as returned by the Clash Royale API.
        player_tag (str): The tag of the player whose name is being retrieved.

    Returns:
        str: The player's name if found, otherwise the given `player_tag`.
    """

    # battles[0] is the newest/earliest battle, so chances are this is the actual current name.
    # Easiest way to get the actual name would be to use the get_player_info of the clash_royale_api module,
    # but extracting it from the battle log, which is already being fetched, saves one API-call per cycle per player
    battle = battles[0]  # Take first battle of battles in the list

    # Reference player is always found in team
    for player in battle.get("team"):
        # Check if it's the reference player
        if player.get("tag") == player_tag:
            return player.get("name")

    return player_tag  # Default to the tag if the name couldn't be found
 b