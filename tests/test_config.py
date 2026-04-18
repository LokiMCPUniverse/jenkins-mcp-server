"""Tests for JenkinsConfig."""

from __future__ import annotations

import pytest

from jenkins_mcp.config import JenkinsConfig


def test_defaults() -> None:
    cfg = JenkinsConfig()
    assert cfg.base_url == "http://localhost:8080"
    assert cfg.username == ""
    assert cfg.api_token == ""
    assert cfg.verify_ssl is True
    assert cfg.timeout == 30.0


def test_env_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JENKINS_BASE_URL", "https://example.ci/")
    monkeypatch.setenv("JENKINS_USERNAME", "alice")
    monkeypatch.setenv("JENKINS_API_TOKEN", "xyz")
    monkeypatch.setenv("JENKINS_VERIFY_SSL", "false")
    monkeypatch.setenv("JENKINS_TIMEOUT", "12")

    cfg = JenkinsConfig()
    assert cfg.base_url == "https://example.ci/"
    assert cfg.normalized_base_url == "https://example.ci"
    assert cfg.username == "alice"
    assert cfg.api_token == "xyz"
    assert cfg.verify_ssl is False
    assert cfg.timeout == 12.0
