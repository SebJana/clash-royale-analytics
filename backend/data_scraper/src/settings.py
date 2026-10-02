from dotenv import load_dotenv, find_dotenv
import os

load_dotenv(find_dotenv())


class Settings:
    """Application settings and configuration."""

    # Scraping starts at most one request every two seconds on each key.
    # Zero disables the optional cap across the whole scraper pool.
    CR_KEY_REQUESTS_PER_SECOND: float = 1.0
    CR_KEY_POOL_REQUESTS_PER_SECOND: float = 0.0

    # Redis Configuration
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    # The scraper writes versioned, reconstructible data only.
    REDIS_HOST: str = "redis-cache"
    KEY_STORE_REDIS_HOST: str = "redis-key-store"
    REDIS_PORT: int = 6379

    # Application Configuration
    INIT_RETRIES: int = 3
    INIT_RETRY_DELAY: float = 3

    # Sleep time between the scraping cycles
    REQUEST_CYCLE_DURATION: float = 5 * 60  # 5 minutes

    # Upon unsuccessful API call
    MAX_RETRIES: int = 5
    BASE_BACKOFF: float = 1.0  # seconds

    # MongoDB Configuration
    MONGO_CLIENT_NAME: str = "cr-analytics-data-scraper"

    # Cache TTL (Time To Live) in seconds
    CACHE_TTL_CARDS: int = 6 * 60 * 60  # 6 hours


# Global settings instance
settings = Settings()
