"""
Simple utilities for Perfecto MCP tools.
"""
import platform
from datetime import datetime
from typing import Optional, Callable

import httpx

from config.token import PerfectoToken
from config.version import __version__
from models.result import BaseResult

so = platform.system()  # "Windows", "Linux", "Darwin"
version = platform.version()  # kernel / build version
release = platform.release()  # ex. "10", "5.15.0-76-generic"
machine = platform.machine()  # ex. "x86_64", "AMD64", "arm64"

ua_part = f"{so} {release}; {machine}"


async def api_request(token: Optional[PerfectoToken], method: str, endpoint: str,
                      result_formatter: Callable = None,
                      result_formatter_params: Optional[dict] = None,
                      **kwargs) -> BaseResult:
    """
    Make an authenticated request to the Perfecto API.
    Handles authentication errors gracefully.
    """
    if not token:
        return BaseResult(
            error="No API token. Set PERFECTO_SECURITY_TOKEN or PERFECTO_SECURITY_TOKEN_FILE env var with security token."
        )

    headers = kwargs.pop("headers", {})
    headers["Perfecto-Authorization"] = token.token
    headers["User-Agent"] = f"perfecto-mcp/{__version__} ({ua_part})"

    timeout = httpx.Timeout(
        connect=15.0,
        read=60.0,
        write=15.0,
        pool=60.0
    )

    async with (httpx.AsyncClient(base_url="", http2=True, timeout=timeout) as client):
        try:
            resp = await client.request(method, endpoint, headers=headers, **kwargs)
            resp.raise_for_status()
            result = resp.json()
            error = None
            if isinstance(result, list) and len(result) > 0 and "userMessage" in result[0]:  # It's an error
                final_result = None
                error = result[0].get("userMessage", None)
            else:
                final_result = result_formatter(result, result_formatter_params) if result_formatter else result
            # TODO: Perfecto doesn't have a general pattern about results and pagination
            return BaseResult(
                result=final_result,
                error=error,
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code in [401, 403]:
                return BaseResult(
                    error="Invalid credentials"
                )
            raise


def get_date_time_iso(timestamp: int) -> Optional[str]:
    if timestamp is None:
        return None
    else:
        return datetime.fromtimestamp(timestamp).isoformat()
