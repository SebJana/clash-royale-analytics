from dotenv import load_dotenv, find_dotenv
import os

load_dotenv(find_dotenv())


class Settings:
    """Application settings and configuration."""

    # API Configuration
    API_TOKEN: str = os.getenv("DATA_SCRAPER_API_KEY", "")

    # Redis Configuration
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379

    # Application Configuration
    INIT_RETRIES: int = 3
    INIT_RETRY_DELAY: float = 3

    # Sleep time between the scraping cycles
    REQUEST_CYCLE_DURATION: float = 15 * 60  # 15 minutes

    # Limitation to call the Clash Royale API
    REQUESTS_PER_SECOND: float = 0.5

    # Upon unsuccessful API call
    MAX_RETRIES: int = 5
    BASE_BACKOFF: float = 1.0  # seconds

    # MongoDB Configuration
    MONGO_CLIENT_NAME: str = "cr-analytics-data-scraper"

    # Cache TTL (Time To Live) in seconds
    CACHE_TTL_CARDS: int = 6 * 60 * 60  # 6 hours


# Global settings instance
settings = Settings()
