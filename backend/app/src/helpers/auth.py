from redis_service import get_redis_json, set_redis_json, build_redis_key


async def get_captcha_text_from_cache(redis_conn, captcha_id: str):
    """Retrieve captcha text from Redis cache using the captcha ID.

    Checks both current and ahead versions of the cache key to find
    the stored captcha text associated with the given captcha ID.

    Args:
        redis_conn: Redis connection instance.
        captcha_id (str): Unique identifier for the captcha challenge.

    Returns:
        str or None: The stored captcha text if found, None otherwise.
    """
    # Check the redis cache for both the current and ahead version
    key = await build_redis_key(
        conn=redis_conn,
        service="crApi",
        resource="captchaText",
        params={"captcha_id": captcha_id},
    )

    key_ahead = await build_redis_key(
        conn=redis_conn,
        service="crApi",
        resource="captchaText",
        version_ahead=True,
        params={"captcha_id": captcha_id},
    )

    text = await get_redis_json(redis_conn, key_ahead) or await get_redis_json(
        redis_conn, key
    )

    return text


async def get_wordle_challenge_from_cache(redis_conn, wordle_id: str):
    """Retrieve wordle challenge data from Redis cache using the wordle ID.

    Checks both current and ahead versions of the cache key to find
    the stored wordle challenge data associated with the given wordle ID.
    Returns both the challenge data and the cache key that was used.

    Args:
        redis_conn: Redis connection instance.
        wordle_id (str): Unique identifier for the wordle challenge.

    Returns:
        tuple[dict | None, str | None]: A tuple containing:
            - dict or None: The stored wordle challenge data if found, None otherwise
            - str or None: The Redis cache key that was used, None if no data found
    """
    # Check the redis cache for both the current and ahead version
    key = await build_redis_key(
        conn=redis_conn,
        service="crApi",
        resource="wordleSolution",
        params={"wordle_id": wordle_id},
    )

    key_ahead = await build_redis_key(
        conn=redis_conn,
        service="crApi",
        resource="wordleSolution",
        version_ahead=True,
        params={"wordle_id": wordle_id},
    )

    # Check version ahead
    wordle_challenge = await get_redis_json(redis_conn, key_ahead)

    if wordle_challenge:
        return wordle_challenge, key_ahead

    # Check current version
    wordle_challenge = await get_redis_json(redis_conn, key)

    if wordle_challenge:
        return wordle_challenge, key

    # If neither exist
    return None, None
