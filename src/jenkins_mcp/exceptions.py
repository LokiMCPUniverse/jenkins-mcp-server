"""Exception hierarchy for the Jenkins MCP server."""

from __future__ import annotations


class JenkinsError(Exception):
    """Base error raised by the Jenkins MCP server."""


class AuthenticationError(JenkinsError):
    """Raised when Jenkins rejects the supplied credentials (HTTP 401/403)."""


class NotFoundError(JenkinsError):
    """Raised when a requested Jenkins resource does not exist (HTTP 404)."""


class APIError(JenkinsError):
    """Raised for any other non-success response from the Jenkins API."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
