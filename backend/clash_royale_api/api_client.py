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


class ClashRoyalePlayerCheckError(Exception):
    """Give the add route a specific failure without exposing raw httpx errors."""

    default_detail = "Clash Royale API request failed"

    def __init__(self):
        self.detail = self.default_detail
        super().__init__(self.detail)


class ClashRoyaleInvalidTagError(ClashRoyalePlayerCheckError):
    default_detail = "Invalid player tag"


class ClashRoyalePlayerNotFoundError(ClashRoyalePlayerCheckError):
    default_detail = "Player not found"


class ClashRoyaleAuthError(ClashRoyalePlayerCheckError):
    default_detail = "Clash Royale rejected the API token or IP address"


class ClashRoyaleConnectionError(ClashRoyalePlayerCheckError):
    default_detail = "Clash Royale API could not be reached"


class ClashRoyaleInvalidResponseError(ClashRoyalePlayerCheckError):
    default_detail = "Clash Royale API returned no player name"


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
    def check_tag_syntax(player_tag: str) -> bool:
        """
        Check for one leading '#', 4-12 tag characters, and the Supercell alphabet.

        Args:
            player_tag (str): The player tag starting with '#' (e.g., "#YYRJQY28")

        Returns:
            bool: True if valid, False otherwise
        """

        # Strip the tag
        tag = player_tag.strip()

        if not tag.startswith("#") or tag.count("#") != 1:
            return False

        core = tag[1:]  # Part without the leading '#'

        # NOTE Match the frontend's current 4-12 limit. Update both validators if Clash
        # Royale starts (or already is) issuing shorter or longer tags.
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
            response (Any): Parsed API response.

        Raises:
            ClashRoyaleMaintenanceError: If the API is in maintenance mode.
        """
        reason = response[0] if isinstance(response, list) and response else response
        if isinstance(reason, dict) and reason.get("reason") == "inMaintenance":
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
        # An error response can still contain the maintenance reason.
        if resp.is_error:
            try:
                self._check_maintenance(resp.json())
            except ValueError:
                pass
        resp.raise_for_status()  # will raise httpx.HTTPStatusError on 4xx/5xx

        payload = resp.json()
        self._check_maintenance(payload)
        return payload

    async def check_connection(self):
        await self.get_cards()

    async def check_existing_player(self, player_tag: str):
        """
        Validates the tag syntax and verifies the a player with that tag exists
        by fetching the player profile from the Clash Royale API.

        Args:
            player_tag (str): The player tag starting with '#' (e.g., "#YYRJQY28")

        Returns:
            str: The player's name when the API confirms the player exists.

        Raises:
            ClashRoyalePlayerCheckError: If the tag or API response is invalid,
                or the Clash Royale API rejects or cannot complete the request.
            ClashRoyaleMaintenanceError: If Clash Royale is in maintenance.
        """

        player_tag = player_tag.strip()
        if not self.check_tag_syntax(player_tag):
            raise ClashRoyaleInvalidTagError()

        try:
            player_info = await self.get_player_info(player_tag)
        except httpx.HTTPStatusError as e:
            # Only 404 proves the player is missing. Auth and API failures need
            # their own errors so the add route does not call them "not found".
            status = e.response.status_code
            if status == 404:
                raise ClashRoyalePlayerNotFoundError() from e
            if status in (401, 403):
                raise ClashRoyaleAuthError() from e
            raise ClashRoyalePlayerCheckError() from e
        except httpx.RequestError as e:
            raise ClashRoyaleConnectionError() from e

        # A successful request without a name does not prove the tag is missing.
        # This should not happen if the CR API is working as expected.
        if not isinstance(player_info, dict) or not player_info.get("name"):
            raise ClashRoyaleInvalidResponseError()

        return player_info["name"]

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
