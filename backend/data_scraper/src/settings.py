from dotenv import load_dotenv, find_dotenv
import os

load_dotenv(find_dotenv())


class Settings:
    """Application settings and configuration."""

    # Scraping starts at most one request per second on each key.
    # Zero disables the optional cap across the whole scraper pool.
    CR_KEY_REQUESTS_PER_SECOND: float = 1.0
    CR_KEY_POOL_REQUESTS_PER_SECOND: float = 0.0

    # Redis Configuration
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    # The scraper only writes reconstructible data here (the card and game
    # mode lists).
    REDIS_HOST: str = "redis-cache"
    # Key leases, the scraping schedules, capacity, and metrics. Never evicted.
    KEY_STORE_REDIS_HOST: str = "redis-key-store"
    REDIS_PORT: int = 6379

    # Application Configuration
    INIT_RETRIES: int = 3
    INIT_RETRY_DELAY: float = 3

    # Battle sync intervals
    # NOTE The battle log only returns the last ~25 battles. A player who plays
    # more battles than that between two syncs loses the older ones for good.
    # Shortest interval; small deployments sync every player this often.
    MIN_SYNC_INTERVAL: float = 5 * 60  # 5 minutes
    # Longest interval, for idle players and for an overloaded key pool.
    # At ~3 minutes per battle, 60 minutes are ~20 battles, still inside the
    # battle log window when an idle player suddenly starts playing.
    MAX_SYNC_INTERVAL: float = 60 * 60  # 60 minutes
    # NOTE Entries the battle log endpoint returns at most. A full log that
    # does not reach back to the stored watermark may have lost battles.
    BATTLE_LOG_SIZE: int = 25

    # Activity based adjustment of a player's next interval
    # A sync with at least this many new battles counts as high activity; the
    # player is synced sooner, at the base interval times the factor below.
    HIGH_ACTIVITY_BATTLES: int = 12
    HIGH_ACTIVITY_INTERVAL_FACTOR: float = 0.5
    # Above this base interval the factor rises linearly to 1 at
    # MAX_SYNC_INTERVAL. Under full load even the most active players then
    # sync at the longest interval, which keeps admission at the worst case
    # of one request per player per MAX_SYNC_INTERVAL.
    HIGH_ACTIVITY_FADE_START: float = 30 * 60  # 30 minutes
    # A sync without new battles stretches the previous interval by this
    # factor, up to MAX_SYNC_INTERVAL. Idle accounts then cost fewer requests.
    IDLE_INTERVAL_GROWTH: float = 1.5

    # Capacity planning
    # Share of the raw key rate (usable keys x requests per second) that is
    # planned for. The rest is headroom for retries, 429 cooldowns, and cards.
    # New players are admitted while every tracked player, all of them active
    # and with daily profiles, could still be synced within MAX_SYNC_INTERVAL.
    CAPACITY_UTILIZATION: float = 0.8

    # Profile snapshots
    # Profile stats (trophies, wins, level) only change when the player plays.
    # A player with battles since the last refresh is refreshed again after the
    # minimum interval; without battles the interval grows up to the maximum.
    PROFILE_MIN_INTERVAL: float = 24 * 60 * 60  # 1 day
    PROFILE_MAX_INTERVAL: float = 7 * 24 * 60 * 60  # 7 days
    # Each refresh without battles since the previous one multiplies the
    # interval by this factor: 1 -> 2 -> 4 -> (8 but capped at) 7 days. Steeper than battles
    # (IDLE_INTERVAL_GROWTH), since a late profile is only stale, never lost.
    PROFILE_IDLE_GROWTH: float = 2.0
    # Profiles only run when no battle sync is due, unless they are overdue by
    # more than this. A busy pool then still refreshes every profile eventually,
    # through one worker that takes overdue profiles first.
    PROFILE_MAX_LATENESS: float = 6 * 60 * 60  # 6 hours
    # Retry delay after a failed profile refresh
    PROFILE_RETRY_DELAY: float = 30 * 60  # 30 minutes

    # A claimed player is due again after this time if its worker never acks,
    # e.g. because the container stopped. Has to exceed the longest job:
    # one Clash Royale request budget (30 s) plus the Mongo writes.
    CLAIM_TTL: float = 2 * 60  # 2 minutes
    # A job is cancelled after this time, so it ends while its claim is still
    # owned and cannot overlap a second job of the same player. Has to stay
    # below CLAIM_TTL and above the request budget (30 s) plus Mongo writes.
    JOB_TIMEOUT: float = 90  # seconds

    # Workers per scraper process. Each worker processes one player at a time,
    # so enough workers are needed to keep every usable key busy while other
    # workers wait on Mongo. Recomputed from the usable key count on every
    # reconciliation, within the min/max bounds.
    WORKERS_PER_KEY_REQUEST_PER_SECOND: float = 3.0
    MIN_WORKERS: int = 2
    MAX_WORKERS: int = 64

    # Longest time an idle worker sleeps before checking the schedule again.
    # Newly added players are picked up within this time.
    IDLE_POLL_INTERVAL: float = 5  # seconds

    # Retry delays for a failed battle sync, doubled per consecutive failure
    FAILURE_BACKOFF_BASE: float = 30  # seconds
    FAILURE_BACKOFF_MAX: float = 30 * 60  # 30 minutes
    # A 404 means the account is gone or the tag became invalid. The retry
    # delay starts at the base interval, so a single glitch costs one sync at
    # most, and doubles up to this maximum.
    NOT_FOUND_RETRY_MAX: float = 6 * 60 * 60  # 6 hours
    # A player is untracked after this many consecutive 404s, and only if the
    # first of them is at least NOT_FOUND_MIN_SPAN old.
    NOT_FOUND_DEACTIVATE_COUNT: int = 3
    NOT_FOUND_MIN_SPAN: float = 24 * 60 * 60  # 24 hours
    # Delay for players claimed while the Clash Royale API went into maintenance
    MAINTENANCE_RETRY_DELAY: float = 60  # seconds

    # How often the schedules are compared with the tracked players in Mongo.
    # Also recomputes the capacity and resizes the worker pool.
    RECONCILE_INTERVAL: float = 5 * 60  # 5 minutes

    # How often newly seen game modes are written to Mongo
    GAME_MODES_FLUSH_INTERVAL: float = 60  # seconds
    # How often the cached game mode list is rebuilt from Mongo without a new
    # mode. Bounds how long the list stays missing after an eviction.
    GAME_MODES_CACHE_REFRESH_INTERVAL: float = 10 * 60  # 10 minutes

    # How often the card list is fetched from the Clash Royale API
    CARDS_REFRESH_INTERVAL: float = 6 * 60 * 60  # 6 hours
    # Retry delay if a card refresh failed
    CARDS_RETRY_DELAY: float = 5 * 60  # 5 minutes
    # How often a missing card cache entry is restored from Mongo between
    # refreshes. Bounds how long the API reads Mongo after an eviction.
    CARDS_CACHE_CHECK_INTERVAL: float = 10 * 60  # 10 minutes

    # Monitoring
    # How often the metrics snapshot is written to Redis
    METRICS_INTERVAL: float = 10  # seconds
    # Time window the throughput counters cover
    METRICS_WINDOW: float = 60  # seconds
    # How often a throughput and schedule summary is logged
    STATUS_LOG_INTERVAL: float = 60  # seconds
    # Port of the read-only status endpoint inside the container. Compose
    # publishes it on the host's loopback interface only.
    STATUS_PORT: int = 9100

    # MongoDB Configuration
    MONGO_CLIENT_NAME: str = "cr-analytics-data-scraper"

    # Cache TTL (Time To Live) in seconds
    # Twice the refresh interval keeps the cards cached if one refresh fails
    CACHE_TTL_CARDS: int = 2 * CARDS_REFRESH_INTERVAL
    # Twice the refresh interval keeps the game modes cached if one refresh fails
    CACHE_TTL_GAME_MODES: int = int(2 * GAME_MODES_CACHE_REFRESH_INTERVAL)


# Global settings instance
settings = Settings()
