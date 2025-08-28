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
    INIT_SLEEP_DURATION: int = 60  # seconds
    
    INIT_SLEEP_DURATION = 60 # 60 seconds
    
    # Sleep time between the scraping cycles
    REQUEST_CYCLE_DURATION = 15 * 60 # 15 minutes

    # Limitation to call the Clash Royale API
    REQUESTS_PER_SECOND = 0.5
    
    # Upon unsuccessful API call
    MAX_RETRIES = 5
    BASE_BACKOFF = 1.0 # seconds
    
    
    # MongoDB Configuration
    MONGO_CLIENT_NAME: str = "cr-analytics-data-scraper"
    
    # Cache TTL (Time To Live) in seconds    
    CACHE_TTL_CARDS: int = 6 * 60 * 60  # 6 hours

# Global settings instance
settings = Settings()
