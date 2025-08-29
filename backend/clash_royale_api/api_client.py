import httpx

CLASH_BASE_URL = "https://api.clashroyale.com/v1"
ALPHABET = set("0289PYLQGRJCUV")  # Supercell tag alphabet


class ClashRoyaleMaintenanceError(Exception):
    """Raised when the Clash Royale API is in maintenance mode."""

    def __init__(
        self,
        detail: str = "Clash Royale API is in maintenance. Try again later.",
        code: int = 503,
    ):
        super().__init__(detail)
        self.detail = detail
        self.code = code


class ClashRoyaleAPI:
    """
    Async Clash Royale API client (single API key, no rotation).
    Reuses one httpx.AsyncClient per instance for connection pooling.
    """

    def __init__(
        self, api_key: str, base_url: str = CLASH_BASE_URL, timeout_s: float = 5.0
    ):
        if not api_key or not api_key.strip():
            raise ValueError("API key must be a non-empty string.")
        self._api_key = api_key.strip()
        self._base_url = base_url.rstrip("/")  # Always remove trailing "/" of base url
        self._client: httpx.AsyncClient = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(
                connect=timeout_s, read=timeout_s, write=timeout_s, pool=timeout_s
            ),
            headers={"Accept": "application/json", "User-Agent": "cr-analytics"},
        )

    # --- helpers -------------------------------------------------------------
    @staticmethod
    def check_tag_syntax(player_tag: str):
        """
        Checks wether the player tag starts with a '#' and has the correct length
        and matches the Supercell alphabet.

        Args:
            player_tag (str): The player tag starting with '#' (e.g., "#YYRJQY28")

        Returns:
            bool: True if valid, False otherwise
        """

        ALPHABET = set("0289PYLQGRJCUV")  # Supercell-Tag-Alphabet

        # Strip the tag
        tag = player_tag.strip()

        # Missing the starting code symbol
        if not tag.startswith("#"):
            return False

        core = tag[1:]  # Part without the leading '#'

        # TODO check actual max or min length
        # Invalid length
        if len(core) < 4 or len(core) > 12:
            return False

        # Check if the tag without the '#' is only numbers and upper letters
        if not all(ch in ALPHABET for ch in core):
            return False

        # Valid if all checks passed
        return True

    @staticmethod
    def _url_encode_player_tag(player_tag: str):
        """
        URL encodes a Clash Royale player tag for use in API requests.

        Replaces the '#' character with '%23' to make the player tag URL-safe
        for use in HTTP requests to the Clash Royale API.

        Args:
            player_tag (str): The player tag starting with '#' (e.g., "#YYRJQY28")

        Returns:
            str: URL-encoded player tag (e.g., "%23YYRJQY28")
        """
        return player_tag.replace("#", "%23")

    @staticmethod
    def _check_maintenance(response):
        """
        Checks if the Clash Royale API is in maintenance mode.

        Args:
            response (Any): The API response (usually a list of dicts)

        Raises:
            ClashRoyaleMaintenanceError: If the API is in maintenance mode.
        """
        if (
            isinstance(response, list)
            and len(response) > 0
            and response[0].get("reason") == "inMaintenance"
        ):
            raise ClashRoyaleMaintenanceError(
                "Clash Royale API is in maintenance mode. Try again later."
            )

    async def _request(self, endpoint: str):
        """
        Makes an authenticated HTTP GET request to the Clash Royale API.

        Sends a GET request to the specified endpoint with the API key in the
        Authorization header. Automatically raises an exception for HTTP error
        status codes and returns the JSON response.

        Args:
            endpoint (str): The API endpoint path (e.g., "/players/{tag}")
            already with the player tag url encoded, if needed in the endpoint

        Returns:
            dict: JSON response data from the API

        Raises:
            RuntimeError: If the HTTP client is closed
            HTTPStatusError: If the API request fails (4xx/5xx status codes)
            RequestException: If there are network connectivity issues
        """

        if self._client is None:
            raise RuntimeError(
                "HTTP client is closed. Create a new instance or call within an async context."
            )

        resp = await self._client.get(
            endpoint,
            headers={"Authorization": f"Bearer {self._api_key}"},
        )
        resp.raise_for_status()  # will raise httpx.HTTPStatusError on 4xx/5xx

        # Check for maintenance
        self._check_maintenance(resp)

        return resp.json()

    async def check_connection(self):
        await self.get_cards()

    async def check_existing_player(self, player_tag: str):
        """
        Validates the tag syntax and verifies the a player with that tag exists
        by fetching the player profile from the Clash Royale API.

        Args:
            player_tag (str): The player tag starting with '#' (e.g., "#YYRJQY28")

        Returns:
            bool: True if syntax is valid AND the API confirms the player exists; else False.
        """

        if not self.check_tag_syntax(player_tag):
            return False

        # If no error on request --> player with that tag exists
        try:
            _ = await self.get_player_info(player_tag)
            return True
        except Exception:
            return False

    async def get_player_battle_logs(self, player_tag: str):
        """
        Fetches battle logs for a specific player from the Clash Royale API.

        Makes an HTTP GET request to the Clash Royale API to retrieve the battle
        history for the specified player. The response contains a list of recent
        battle logs with detailed information about each match.

        Args:
            player_tag (str): The player tag (e.g., "#YYRJQY28")

        Returns:
            list: List of battle log dictionaries from the API response

        Raises:
            HTTPError: If the API request fails (4xx/5xx status codes)
            RequestException: If there are network connectivity issues
        """

        if not self.check_tag_syntax(player_tag):
            raise ValueError(f"Invalid player tag syntax: {player_tag!r}")

        tag = self._url_encode_player_tag(player_tag)
        return await self._request(f"/players/{tag}/battlelog")

    async def get_player_info(self, player_tag: str):
        """
        Fetches player information for a specific player from the Clash Royale API.

        Makes an HTTP GET request to the Clash Royale API to retrieve the profile
        information for the specified player.

        Args:
            player_tag (str): The player tag (e.g., "#YYRJQY28")

        Returns:
            list: All of the player's stats and information

        Raises:
            HTTPError: If the API request fails (4xx/5xx status codes)
            RequestException: If there are network connectivity issues
        """

        if not self.check_tag_syntax(player_tag):
            raise ValueError(f"Invalid player tag syntax: {player_tag!r}")

        tag = self._url_encode_player_tag(player_tag)
        return await self._request(f"/players/{tag}")

    async def get_cards(self):
        """
        Fetches every card's information from the Clash Royale API.

        Makes an HTTP GET request to the Clash Royale API to retrieve all game cards.

        Returns:
            list: All cards in the game as items

        Raises:
            HTTPError: If the API request fails (4xx/5xx status codes)
            RequestException: If there are network connectivity issues
        """

        return await self._request("/cards")

    async def close(self):
        """
        Closes the HTTP client and releases all resources.

        Should be called when the API client is no longer needed to properly
        clean up connections and avoid resource leaks.
        """
        if self._client is not None:
            await self._client.aclose()
            self._client = None
