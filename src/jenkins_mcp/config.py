"""Configuration for the Jenkins MCP server."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class JenkinsConfig(BaseSettings):
    """Jenkins server connection configuration.

    Values are loaded from environment variables using the ``JENKINS_`` prefix.
    """

    model_config = SettingsConfigDict(
        env_prefix="JENKINS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    base_url: str = Field(
        default="http://localhost:8080",
        description="Base URL of the Jenkins controller (no trailing slash).",
    )
    username: str = Field(
        default="",
        description="Jenkins username used for HTTP basic authentication.",
    )
    api_token: str = Field(
        default="",
        description="Jenkins API token (or password) used for basic authentication.",
    )
    verify_ssl: bool = Field(
        default=True,
        description="Whether to verify TLS certificates when talking to Jenkins.",
    )
    timeout: float = Field(
        default=30.0,
        description="HTTP timeout in seconds for all Jenkins API calls.",
    )

    @property
    def normalized_base_url(self) -> str:
        """Return the base URL with trailing slashes stripped."""
        return self.base_url.rstrip("/")
