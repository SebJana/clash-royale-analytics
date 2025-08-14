from datetime import datetime

def adjust_card_levels(cards):
    # Clash Royale changed the level system, but their API still returns the old
    # levels. Back then all cards started at level 1 and could be leveled up.
    # Level 13 for common cards, level 11 for rare cards, level 8 for epic cards, ...
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
    # Remove fields that aren't necessary for storing
    # Keep name and id for each card, so that when id should ever change
    # the already stored data can still be connected to the card via the name
    keys_to_remove = ["maxLevel", "maxEvolutionLevel", "rarity", "starLevel", "elixirCost", "iconUrls"]

    for card in cards:
        for key in keys_to_remove:
            card.pop(key, None)

def clean_battle_log_list(battle_logs, player_tag):
    for battle in battle_logs:
        # Add a reference player tag to each battle
        # Tag combined with time is unique identifier for each battle
        battle['referencePlayerTag'] = player_tag

        # Turn the date/time format into ISO time
        battle_time = battle.get('battleTime')
        battle_time = datetime.strptime(battle_time, "%Y%m%dT%H%M%S.000Z")
        battle['battleTime'] = battle_time.strftime("%Y-%m-%d %H:%M:%S")

        # For each battle in the format and clean it
        clean_battle_log(battle)

        # Remove the unnecessary stats from each battle
        keys_to_remove = ["deckSelection", "isHostedMatch", "leagueNumber", "isLadderTournament"]

        for key in keys_to_remove:
            battle.pop(key, None)
    
    return battle_logs

def clean_battle_log(battle_log):
    for team_player in battle_log.get("team"):
        # Remove the clan for each player 
        team_player.pop("clan", None)

        # Clean and adjust the own/teammate deck cards
        adjust_card_levels(team_player.get("cards"))
        remove_unnecessary_card_fields(team_player.get("cards"))

        # Clean and adjust the own/teammate support card(s) [Tower Troop]
        adjust_card_levels(team_player.get("supportCards"))
        remove_unnecessary_card_fields(team_player.get("supportCards"))

        team_player.pop("globalRank", None)

    for opponent_player in battle_log.get("opponent"):
        # Remove the clan for each player 
        opponent_player.pop("clan", None)

        # Clean and adjust the enemies deck cards
        adjust_card_levels(opponent_player.get("cards"))
        remove_unnecessary_card_fields(opponent_player.get("cards"))

        # Clean and adjust the enemies support card(s) [Tower Troop]
        adjust_card_levels(opponent_player.get("supportCards"))
        remove_unnecessary_card_fields(opponent_player.get("supportCards"))

        opponent_player.pop("globalRank", None)