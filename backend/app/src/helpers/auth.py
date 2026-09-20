from redis_service import RedisConn, build_auth_state_key, get_auth_state_json


async def get_captcha_text_from_state(redis_conn: RedisConn, captcha_id: str):
    """Retrieve CAPTCHA text from the versionless auth-state Redis store.

    Args:
        redis_conn (RedisConn): Versionless Redis connection for auth challenges.
        captcha_id (str): Unique identifier for the captcha challenge.

    Returns:
        str or None: The stored captcha text if found, None otherwise.
    """
    key = build_auth_state_key("captcha", captcha_id)
    return await get_auth_state_json(redis_conn, key)


async def get_wordle_challenge_from_state(redis_conn: RedisConn, wordle_id: str):
    """Retrieve Wordle state using a stable, versionless challenge key.
    Returns both the challenge data and its stable auth-state key.

    Args:
        redis_conn (RedisConn): Versionless Redis connection for auth challenges.
        wordle_id (str): Unique identifier for the wordle challenge.

    Returns:
        tuple[dict | None, str]: A tuple containing:
            - dict or None: The stored wordle challenge data if found, None otherwise
            - str: The auth-state Redis key for updating an existing challenge
    """
    key = build_auth_state_key("wordle", wordle_id)
    return await get_auth_state_json(redis_conn, key), key
