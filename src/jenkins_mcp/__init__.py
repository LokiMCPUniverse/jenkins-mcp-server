"""Jenkins MCP Server - Model Context Protocol server for Jenkins CI/CD integration."""

from __future__ import annotations

from .client import JenkinsClient
from .config import JenkinsConfig
from .exceptions import APIError, AuthenticationError, JenkinsError, NotFoundError
from .server import main, mcp

__version__ = "0.1.0"

__all__ = [
    "APIError",
    "AuthenticationError",
    "JenkinsClient",
    "JenkinsConfig",
    "JenkinsError",
    "NotFoundError",
    "__version__",
    "main",
    "mcp",
]
