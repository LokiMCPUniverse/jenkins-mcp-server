"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from jenkins_mcp.client import JenkinsClient
from jenkins_mcp.config import JenkinsConfig


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Apply pytest-httpx options globally so unused mocks don't fail tests."""
    marker = pytest.mark.httpx_mock(
        assert_all_responses_were_requested=False,
        can_send_already_matched_responses=True,
    )
    for item in items:
        item.add_marker(marker)


@pytest.fixture
def jenkins_config() -> JenkinsConfig:
    return JenkinsConfig(
        base_url="http://jenkins.test",
        username="ci-user",
        api_token="secret-token",
        verify_ssl=False,
        timeout=5,
    )


@pytest.fixture
async def jenkins_client(jenkins_config: JenkinsConfig, httpx_mock) -> JenkinsClient:
    """Provide a JenkinsClient backed by pytest-httpx.

    A default crumb response is pre-registered so tests that exercise POST
    endpoints don't need to repeat it. Tests that need a different crumb
    behavior (e.g. 404) construct their own client.
    """
    httpx_mock.add_response(
        url="http://jenkins.test/crumbIssuer/api/json",
        json={"crumbRequestField": "Jenkins-Crumb", "crumb": "abc123"},
    )
    async with JenkinsClient(jenkins_config) as client:
        yield client
