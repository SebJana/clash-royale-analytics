from fastapi import Request


def get_real_client_ip(request: Request) -> str:
    """
    Extract the real client IP from the request for rate limiting purposes.

    This function handles multiple scenarios to identify unique clients:
    1. Production: Uses real external IPs from proxy headers
    2. Development: Uses User-Agent hashing for Docker NAT scenarios
    3. Fallback: Uses direct client IP when available

    Returns:
        str: The best guess at the real client IP address for rate limiting
    """

    # STEP 1: Check X-Forwarded-For header
    # This header is set by reverse proxies (nginx, load balancers) and contains
    # the chain of IPs: "original_client, proxy1, proxy2"
    # Try to extract the first IP in the chain (the original client)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Get the first IP (original client) from the chain
        first_ip = forwarded_for.split(",")[0].strip()
        # Only use it if it's not a Docker internal IP (172.16.x.x - 172.31.x.x range)
        # Docker internal IPs indicate the user is still behind Docker's NAT
        if first_ip and not first_ip.startswith("172.1"):
            return first_ip

    # STEP 2: Check X-Real-IP header
    # This header is set by nginx's real_ip module and contains the "real" client IP
    # after processing X-Forwarded-For chains and trusted proxy configurations
    real_ip = request.headers.get("X-Real-IP")
    if real_ip and not real_ip.startswith("172.1"):
        return real_ip

    # STEP 3: Try to extract real IP from Referer header (Docker development)
    # In Docker environments, the Referer header often contains the real local IP
    # Example: "http://192.168.178.38/" shows the actual device IP
    referer = request.headers.get("Referer", "")
    if referer:
        try:
            from urllib.parse import urlparse

            parsed = urlparse(referer)
            if parsed.hostname:
                # Check if it's a local network IP (not Docker internal)
                if (
                    parsed.hostname.startswith("192.168.")
                    or parsed.hostname.startswith("10.")
                    or (
                        parsed.hostname.startswith("172.")
                        and not parsed.hostname.startswith("172.1")
                    )
                ):
                    return parsed.hostname
        except (ValueError, AttributeError, TypeError):
            pass  # Continue to fallback methods if parsing fails

    # STEP 4: Fallback to direct client IP from FastAPI
    # This is the immediate client that connected to the server
    # In Docker environments, this will be the nginx container IP
    client_host = request.client.host if request.client else "unknown"

    # STEP 5: Handle Docker development scenario with User-Agent
    # Problem: Docker's port mapping (NAT) causes all local network devices
    # to appear as the same IP (172.18.0.1 - Docker gateway)
    # Solution: Use User-Agent header to differentiate devices for rate limiting
    if client_host.startswith("172.1") or request.headers.get(
        "X-Real-IP", ""
    ).startswith("172.1"):
        # All devices appear as 172.18.0.1
        # Create a unique identifier based on User-Agent header
        # Different devices/browsers have different User-Agent strings:
        # - Chrome on Windows: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/..."
        # - Safari on iPhone: "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)..."
        # - Chrome on Android: "Mozilla/5.0 (Linux; Android 12; SM-G973F)..."
        user_agent = request.headers.get("User-Agent", "")

        # Create MD5 hash of User-Agent to generate consistent device identifier
        # MD5 is sufficient here since we only need device differentiation, not security
        # First 8 characters provide enough uniqueness for local development
        # NOTE: Not a perfect solution, but "unique enough" for those cases
        import hashlib

        device_hash = hashlib.md5(user_agent.encode()).hexdigest()[:8]

        # Return format: "local-{hash}"
        # Examples: "local-3c3e6c9b" (Windows Chrome), "local-ea23dc97" (Android Chrome)
        return f"local-{device_hash}"

    # STEP 6: Final fallback
    # Use the direct client IP if we haven't handled it above
    # This occurs in non-Docker deployments or when we have real external IPs
    return client_host


async def rate_limit_key_func(request: Request) -> str:
    """
    Custom key function for fastapi-limiter to use real client IP.
    This ensures rate limiting works correctly behind reverse proxies (nginx).
    """
    return get_real_client_ip(request)
