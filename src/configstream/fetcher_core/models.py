"""
FetchResult container.
"""

from typing import Any


class FetchResult:
    """Container for fetch results with performance metadata."""

    __slots__ = (
        "success",
        "source",
        "content",
        "error",
        "response_time",
        "status_code",
        "headers",
    )

    def __init__(
        self,
        success: bool,
        source: str,
        content: str = "",
        error: str | None = None,
        response_time: float | None = None,
        status_code: int | None = None,
        headers: dict[str, Any] | None = None,
    ):
        self.success = success
        self.source = source
        self.content = content
        self.error = error
        self.response_time = response_time
        self.status_code = status_code
        self.headers = headers or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "success": self.success,
            "content_length": len(self.content),
            "error": self.error,
            "response_time": self.response_time,
            "status_code": self.status_code,
            "headers": self.headers,
        }


class FetcherError(Exception):
    """Base exception for fetcher-related errors."""


class RateLimitError(FetcherError):
    """Raised when an HTTP 429 Rate Limit is detected."""

    def __init__(self, retry_after: float | None = None):
        self.retry_after = retry_after
        msg = (
            f"Rate limited. Retry after {retry_after:.1f}s"
            if retry_after
            else "Rate limited."
        )
        super().__init__(msg)
