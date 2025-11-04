from dotenv import load_dotenv, find_dotenv
import os

load_dotenv(find_dotenv())


class Settings:
    """Application settings and configuration."""

    # API Configuration
    API_TOKEN: str = os.getenv("APP_API_KEY", "")

    # Redis Configuration
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379

    # Application Configuration
    INIT_RETRIES: int = 3
    INIT_RETRY_DELAY: float = 3

    # MongoDB Configuration
    MONGO_CLIENT_NAME: str = "cr-analytics-api"

    # Maximum time interval that can be requested using a BetweenRequest for decks, cards, stats
    # If none is wanted, just set the limit to an arbitrarily big number
    MAX_TIME_RANGE_DAYS: int = 10 * 365
    # Amount of battles that can be retrieved in one request
    MIN_BATTLES: int = 1
    MAX_BATTLES: int = 20

    # Cache TTL (Time To Live) in seconds
    # Cache is being invalidated in every data scraping cycle
    # Cache data is always as up-to-date as the most recently scraped data from MongoDB
    # Keep TTL still in the minutes to hours range as fallback
    # to not risk having outdated data upon synchronization errors or scraping errors

    CACHE_TTL_CARDS: int = 6 * 60 * 60  # 6 hours
    CACHE_TTL_GAME_MODES: int = 1 * 60 * 60  # 1 hour
    CACHE_TTL_PLAYER_PROFILE: int = 15 * 60  # 15 minutes
    CACHE_TTL_PLAYER_BATTLE_STATS: int = 10 * 60  # 10 minutes
    CACHE_TTL_BATTLES: int = (
        1 * 60
    )  # 1 minutes (short cache time, query params likely to change often with before timestamp. Also no real calculation effort needed for retrieving last battles)
    CACHE_TTL_DECK_STATS: int = 10 * 60  # 10 minutes
    CACHE_TTL_CARD_STATS: int = 10 * 60  # 10 minutes


# Global settings instance
settings = Settings()
