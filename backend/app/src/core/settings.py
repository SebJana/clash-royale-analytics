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
    
    # Cache TTL (Time To Live) in seconds
    # Cache is being invalidated in every data scraping cycle
    # Cache data is always up to, or close to as fresh as the scraped data in the mongo
    # Keep TTL still in the minutes to hours range as fallback 
    # to not risk having outdated data upon synchronization errors or scraping errors
    
    CACHE_TTL_CARDS: int = 6 * 60 * 60  # 6 hours
    CACHE_TTL_PLAYER_PROFILE: int = 15 * 60  # 15 minutes
    CACHE_TTL_PLAYER_BATTLE_STATS: int = 10 * 60 # 10 minutes
    CACHE_TTL_BATTLES: int = 10 * 60  # 10 minutes
    CACHE_TTL_DECK_STATS: int = 10 * 60  # 10 minutes
    CACHE_TTL_CARD_STATS: int = 10 * 60  # 10 minutes

# Global settings instance
settings = Settings()
