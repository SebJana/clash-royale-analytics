from fastapi import Request


async def rate_limit_key_func(request: Request) -> str:
    """Key limits by the trusted client IP and the matched endpoint."""
    client_ip = request.client.host if request.client else "unknown"
    route = request.scope["route"]
    return f"{client_ip}:{request.method}:{route.path}"
