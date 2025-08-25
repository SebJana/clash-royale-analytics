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
    INIT_SLEEP_DURATION: int = 60  # seconds
    
    # MongoDB Configuration
    MONGO_CLIENT_NAME: str = "cr-analytics-api"
    
    # Cache TTL (Time To Live) in seconds
    CACHE_TTL_CARDS: int = 24 * 60 * 60  # 24 hours
    CACHE_TTL_PLAYER_STATS: int = 15 * 60  # 15 minutes
    CACHE_TTL_BATTLES: int = 15 * 60  # 15 minutes
    CACHE_TTL_DECK_STATS: int = 15 * 60  # 15 minutes
    CACHE_TTL_CARD_STATS: int = 15 * 60  # 15 minutes

# Global settings instance
settings = Settings()
