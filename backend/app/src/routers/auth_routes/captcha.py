"""CAPTCHA challenge and answer routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from fastapi_limiter.depends import RateLimiter
from starlette.concurrency import run_in_threadpool

from core.deps import AuthStateConn
from core.settings import settings
from helpers.auth import get_captcha_text_from_state
from helpers.generate_captcha import generate_captcha_string, generate_captcha_image
from helpers.jwt import AvailableTokenTypes, create_access_token
from models.schema import CaptchaAnswerRequest
from redis_service import build_auth_state_key, set_auth_state_json

router = APIRouter()


@router.get("/captcha_id", dependencies=[Depends(RateLimiter(times=5, seconds=60))])
async def get_captcha_id(auth_state_conn: AuthStateConn):
    """Generate a new CAPTCHA ID and store its answer in auth state.

    Challenge keys have no cache version. They remain readable until their TTL
    expires, regardless of data-scraper cache invalidation.

    Args:
        auth_state_conn (AuthStateConn): Versionless auth-state Redis connection.

    Returns:
        dict: Dictionary containing the generated captcha_id.
    """
    text = generate_captcha_string(settings.CAPTCHA_CHAR_LENGTH)
    captcha_id = str(uuid.uuid4())

    key = build_auth_state_key("captcha", captcha_id)
    await set_auth_state_json(
        auth_state_conn,
        key,
        value=text,
        ttl=settings.CACHE_TTL_CAPTCHA_CHALLENGE,
    )

    return {"captcha_id": captcha_id}


@router.get(
    "/captcha_image/{captcha_id}",
    dependencies=[Depends(RateLimiter(times=5, seconds=60))],
    responses={404: {"description": "CAPTCHA challenge expired or not found"}},
)
async def get_captcha_image(auth_state_conn: AuthStateConn, captcha_id: str):

    text = await get_captcha_text_from_state(auth_state_conn, captcha_id=captcha_id)

    if not text:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "CAPTCHA_EXPIRED",
                "message": "CAPTCHA took too long. Restart the CAPTCHA.",
            },
        )

    # ImageCaptcha renders synchronously; run it in a worker thread so other
    # async requests can keep using the event loop while it draws the PNG.
    # TODO potentially pool those to have max X concurrent unique captcha images
    image = await run_in_threadpool(generate_captcha_image, text)

    # Return the image with the session ID in headers
    return Response(
        content=image,
        media_type="image/png",
    )


@router.post(
    "/verify_captcha",
    dependencies=[Depends(RateLimiter(times=5, seconds=60))],
    responses={
        401: {"description": "CAPTCHA answer incorrect"},
        404: {"description": "CAPTCHA challenge expired or not found"},
    },
)
async def get_captcha_token(auth_state_conn: AuthStateConn, req: CaptchaAnswerRequest):

    text = await get_captcha_text_from_state(auth_state_conn, captcha_id=req.captcha_id)

    if not text:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "CAPTCHA_EXPIRED",
                "message": "CAPTCHA took too long. Restart the CAPTCHA.",
            },
        )

    # NOTE: compare with lowercase answer and text, otherwise the captcha is very hard to solve
    # even for a human
    # Check if stored and given answer match
    if req.answer.lower() == text.lower():
        return {
            "captcha_token": create_access_token(
                type=AvailableTokenTypes.CAPTCHA.value,
                expires_minutes=settings.CAPTCHA_TOKEN_EXPIRES_IN,
            )
        }

    raise HTTPException(
        status_code=401,
        detail={
            "code": "CAPTCHA_INCORRECT",
            "message": "The CAPTCHA text doesn't match. Check the image and try again.",
        },
    )
