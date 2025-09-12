import threading


class UniqueGameModes:
    def __init__(self):
        self._lock = threading.Lock()
        self._values = set()

    def add(self, game_mode: str):
        """Add game mode to set if not already present"""
        with self._lock:
            if game_mode not in self._values:
                self._values.add(game_mode)

    def get_values(self):
        """
        Get all unique game modes currently in values
        Returns:
            list: unique game modes
        """
        with self._lock:
            return list(self._values)
