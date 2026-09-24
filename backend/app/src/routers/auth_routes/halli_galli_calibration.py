"""WebSocket protocol for server-verified Halli Galli latency calibration."""

import asyncio
import secrets
import time
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from core.settings import settings
from helpers.halli_galli_calibration import CalibrationError, calculate_calibration_rtt_ms
from helpers.jwt import AvailableTokenTypes, get_access_token_claims
from redis_service import build_auth_state_key, set_auth_state_json


router = APIRouter()


def _is_allowed_calibration_origin(websocket: WebSocket) -> bool:
    """Require the browser origin to be explicitly configured.

    Args:
        websocket (WebSocket): Connection requesting calibration.

    Returns:
        bool: Whether its Origin header is allowed for this game.
    """

    return websocket.headers.get("origin") in settings.HALLI_GALLI_WS_ALLOWED_ORIGINS


def _is_matching_calibration_pong(
    message: object, sequence: int, nonce: str
) -> bool:
    """Check that a pong answers the probe the server just sent.

    Args:
        message (object): JSON frame received from the browser.
        sequence (int): Current probe number.
        nonce (str): Random value sent with this probe.

    Returns:
        bool: Whether this is the matching pong for the current probe.
    """

    # Sequence and nonce reject an old or guessed reply. compare_digest also
    # compares the nonce without timing differences from an early mismatch.
    return (
        isinstance(message, dict)
        and message.get("type") == "pong"
        and type(message.get("sequence")) is int
        and message["sequence"] == sequence
        and isinstance(message.get("nonce"), str)
        and secrets.compare_digest(message["nonce"], nonce)
    )


async def _fail_calibration(websocket: WebSocket, reason: str) -> None:
    """Tell an accepted socket why calibration failed, then close it.

    Args:
        websocket (WebSocket): Accepted connection being rejected.
        reason (str): Error code sent to the browser.

    Returns:
        None: The failure frame is sent and the socket is closed.
    """

    await websocket.send_json({"type": "calibration_failed", "reason": reason})
    await websocket.close(code=status.WS_1008_POLICY_VIOLATION)


@router.websocket("/halli-galli/calibration")
async def calibrate_halli_galli_latency(websocket: WebSocket):
    """Measure browser round-trip time with server-timed, nonce-bound probes.

    Args:
        websocket (WebSocket): Browser connection carrying the Wordle token.

    Returns:
        None: Sends a short-lived calibration ID or a failure frame, then closes.
    """

    # The browser sends its Wordle token in the first frame because browser
    # WebSocket APIs cannot attach the normal Authorization header.
    if not _is_allowed_calibration_origin(websocket):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    try:
        authentication = await asyncio.wait_for(
            websocket.receive_json(),
            timeout=settings.HALLI_GALLI_CALIBRATION_PROBE_TIMEOUT_SECONDS,
        )
    except WebSocketDisconnect:
        return
    except (TimeoutError, ValueError, TypeError):
        await _fail_calibration(websocket, "authentication_timeout_or_invalid")
        return

    if (
        not isinstance(authentication, dict)
        or authentication.get("type") != "authenticate"
    ):
        await _fail_calibration(websocket, "authentication_required")
        return

    wordle_token = authentication.get("wordle_token")
    if not isinstance(wordle_token, str):
        await _fail_calibration(websocket, "invalid_wordle_token")
        return

    claims = get_access_token_claims(wordle_token, AvailableTokenTypes.WORDLE.value)
    if claims is None:
        await _fail_calibration(websocket, "invalid_wordle_token")
        return

    # Do not send any probes until the token has been checked. Their timings
    # belong to this one connection and this exact Wordle token's JTI.
    await websocket.send_json({"type": "authenticated"})
    rtts_ms: list[float] = []

    for sequence in range(settings.HALLI_GALLI_CALIBRATION_PROBE_COUNT):
        # Start timing on the server before sending. The browser only echoes
        # the probe; it never supplies a claimed RTT or timestamp.
        nonce = secrets.token_urlsafe(24)
        sent_at_ns = time.monotonic_ns()
        await websocket.send_json(
            {"type": "probe", "sequence": sequence, "nonce": nonce}
        )

        try:
            pong = await asyncio.wait_for(
                websocket.receive_json(),
                timeout=settings.HALLI_GALLI_CALIBRATION_PROBE_TIMEOUT_SECONDS,
            )
        except TimeoutError:
            # A missed probe is tolerated only while enough later replies pass
            # the quality gate. A late pong will fail nonce/sequence validation.
            continue
        except (WebSocketDisconnect, ValueError, TypeError):
            return

        if not _is_matching_calibration_pong(pong, sequence, nonce):
            await _fail_calibration(websocket, "invalid_probe_reply")
            return

        rtts_ms.append((time.monotonic_ns() - sent_at_ns) / 1_000_000)

    try:
        network_delay_rtt_ms = calculate_calibration_rtt_ms(rtts_ms)
    except CalibrationError as error:
        await _fail_calibration(websocket, str(error))
        return

    # Store the measured RTT under a short-lived ID bound to the Wordle token.
    # The game-start route still has a temporary fixed-RTT fallback and does
    # not consume this ID yet.
    calibration_id = str(uuid.uuid4())
    calibration_key = build_auth_state_key("halli_galli_calibration", calibration_id)
    await set_auth_state_json(
        websocket.app.state.auth_state_redis,
        calibration_key,
        value={
            "wordle_jti": claims["jti"],
            "network_delay_rtt_ms": network_delay_rtt_ms,
        },
        ttl=settings.HALLI_GALLI_CALIBRATION_TTL_SECONDS,
    )
    print(
        "Temporary Halli Galli calibration measurement: "
        f"{network_delay_rtt_ms} ms"
    )
    await websocket.send_json(
        {
            "type": "calibration_complete",
            "calibration_id": calibration_id,
        }
    )
    await websocket.close()
