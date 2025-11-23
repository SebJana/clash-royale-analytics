from .connection import MongoConn
from .battles_read import (
    get_battles_count,
    print_first_battles,
    get_last_battles,
    get_decks_win_percentage,
    get_cards_win_percentage,
    get_daily_stats,
)
from .battles_write import insert_battles

from .players_read import (
    get_tracked_player_tags,
    get_tracked_players,
    check_player_tracked,
    get_players_count,
)
from .players_write import (
    insert_tracked_player,
    set_player_name,
    deactivate_tracked_player,
)

from .game_modes_write import insert_game_modes
from .game_modes_read import get_game_modes

__all__ = [
    "MongoConn",
    # battles
    ## read
    "get_battles_count",
    "print_first_battles",
    "get_last_battles",
    "get_decks_win_percentage",
    "get_cards_win_percentage",
    "get_daily_stats",
    ## write
    "insert_battles",
    # players
    ## read
    "get_tracked_player_tags",
    "get_tracked_players",
    "check_player_tracked",
    "get_players_count",
    ## write
    "insert_tracked_player",
    "set_player_name",
    "deactivate_tracked_player",
    # game_modes
    ## read
    "get_game_modes",
    ## write
    "insert_game_modes",
]
