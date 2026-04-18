"""Tests for JenkinsClient."""

from __future__ import annotations

import base64

import pytest

from jenkins_mcp.client import JenkinsClient
from jenkins_mcp.config import JenkinsConfig
from jenkins_mcp.exceptions import APIError, AuthenticationError, NotFoundError


# ------------------------------------------------------------------ auth/crumb
async def test_basic_auth_header_is_sent(jenkins_client: JenkinsClient, httpx_mock) -> None:
    httpx_mock.add_response(
        url="http://jenkins.test/api/json?tree=jobs%5Bname%2Curl%2Ccolor%5D",
        json={"jobs": []},
    )

    await jenkins_client.list_jobs()

    # Find a non-crumb request to validate the Authorization header.
    relevant = [r for r in httpx_mock.get_requests() if r.url.path == "/api/json"]
    assert relevant, "expected at least one /api/json request"
    auth_header = relevant[0].headers.get("Authorization")
    expected = "Basic " + base64.b64encode(b"ci-user:secret-token").decode()
    assert auth_header == expected


async def test_crumb_fetched_and_cached(jenkins_client: JenkinsClient, httpx_mock) -> None:
    httpx_mock.add_response(
        url="http://jenkins.test/job/demo/build",
        status_code=201,
        headers={"Location": "http://jenkins.test/queue/item/7/"},
    )
    httpx_mock.add_response(
        url="http://jenkins.test/job/demo/1/stop",
        status_code=200,
    )

    await jenkins_client.trigger_build("demo")
    await jenkins_client.stop_build("demo", 1)

    crumb_requests = [
        r for r in httpx_mock.get_requests() if r.url.path == "/crumbIssuer/api/json"
    ]
    assert len(crumb_requests) == 1, "crumb should be fetched exactly once"

    build_request = next(
        r for r in httpx_mock.get_requests() if r.url.path == "/job/demo/build"
    )
    assert build_request.headers.get("Jenkins-Crumb") == "abc123"


async def test_crumb_404_is_handled_gracefully(
    jenkins_config: JenkinsConfig, httpx_mock
) -> None:
    httpx_mock.add_response(
        url="http://jenkins.test/crumbIssuer/api/json", status_code=404
    )
    httpx_mock.add_response(
        url="http://jenkins.test/job/demo/build", status_code=201
    )

    async with JenkinsClient(jenkins_config) as client:
        result = await client.trigger_build("demo")

    assert result["status_code"] == 201
    build_request = next(
        r for r in httpx_mock.get_requests() if r.url.path == "/job/demo/build"
    )
    assert "Jenkins-Crumb" not in build_request.headers


# ------------------------------------------------------------------ tools
async def test_list_jobs(jenkins_client: JenkinsClient, httpx_mock) -> None:
    httpx_mock.add_response(
        url="http://jenkins.test/api/json?tree=jobs%5Bname%2Curl%2Ccolor%5D",
        json={"jobs": [{"name": "a", "url": "u", "color": "blue"}]},
    )
    jobs = await jenkins_client.list_jobs()
    assert jobs == [{"name": "a", "url": "u", "color": "blue"}]


async def test_list_jobs_folder_scoped(jenkins_client: JenkinsClient, httpx_mock) -> None:
    httpx_mock.add_response(
        url="http://jenkins.test/job/team/job/app/api/json?tree=jobs%5Bname%2Curl%2Ccolor%5D",
        json={"jobs": []},
    )
    await jenkins_client.list_jobs("team/app")


async def test_get_job(jenkins_client: JenkinsClient, httpx_mock) -> None:
    httpx_mock.add_response(
        url="http://jenkins.test/job/demo/api/json",
        json={"name": "demo", "buildable": True},
    )
    result = await jenkins_client.get_job("demo")
    assert result["name"] == "demo"


async def test_trigger_build_no_params(jenkins_client: JenkinsClient, httpx_mock) -> None:
    httpx_mock.add_response(
        url="http://jenkins.test/job/demo/build",
        status_code=201,
        headers={"Location": "http://jenkins.test/queue/item/7/"},
    )
    result = await jenkins_client.trigger_build("demo")
    assert result["status_code"] == 201
    assert result["queue_location"] == "http://jenkins.test/queue/item/7/"


async def test_trigger_build_with_params(jenkins_client: JenkinsClient, httpx_mock) -> None:
    httpx_mock.add_response(
        url="http://jenkins.test/job/demo/buildWithParameters",
        status_code=201,
        headers={"Location": "http://jenkins.test/queue/item/9/"},
    )
    result = await jenkins_client.trigger_build("demo", {"BRANCH": "main", "DEBUG": "1"})
    assert result["status_code"] == 201

    request = next(
        r
        for r in httpx_mock.get_requests()
        if r.url.path == "/job/demo/buildWithParameters"
    )
    body = request.content.decode()
    assert "BRANCH=main" in body
    assert "DEBUG=1" in body


async def test_get_build(jenkins_client: JenkinsClient, httpx_mock) -> None:
    httpx_mock.add_response(
        url="http://jenkins.test/job/demo/42/api/json",
        json={"number": 42, "result": "SUCCESS"},
    )
    result = await jenkins_client.get_build("demo", 42)
    assert result["result"] == "SUCCESS"


async def test_get_build_log_returns_text(jenkins_client: JenkinsClient, httpx_mock) -> None:
    log = "Started by user\nBuild step A\nFinished: SUCCESS\n"
    httpx_mock.add_response(
        url="http://jenkins.test/job/demo/42/consoleText",
        text=log,
    )
    assert await jenkins_client.get_build_log("demo", 42) == log


async def test_stop_build(jenkins_client: JenkinsClient, httpx_mock) -> None:
    httpx_mock.add_response(
        url="http://jenkins.test/job/demo/42/stop", status_code=200
    )
    result = await jenkins_client.stop_build("demo", 42)
    assert result["status_code"] == 200


async def test_list_builds(jenkins_client: JenkinsClient, httpx_mock) -> None:
    httpx_mock.add_response(
        url="http://jenkins.test/job/demo/api/json?tree=builds%5Bnumber%2Cresult%2Ctimestamp%2Cduration%5D%7B0%2C5%7D",
        json={"builds": [{"number": 3, "result": "SUCCESS", "timestamp": 1, "duration": 2}]},
    )
    result = await jenkins_client.list_builds("demo", limit=5)
    assert result[0]["number"] == 3


async def test_list_queue(jenkins_client: JenkinsClient, httpx_mock) -> None:
    httpx_mock.add_response(
        url="http://jenkins.test/queue/api/json",
        json={"items": [{"id": 11, "why": "waiting"}]},
    )
    result = await jenkins_client.list_queue()
    assert result[0]["id"] == 11


async def test_cancel_queue_item(jenkins_client: JenkinsClient, httpx_mock) -> None:
    httpx_mock.add_response(
        url="http://jenkins.test/queue/cancelItem?id=11", status_code=204
    )
    result = await jenkins_client.cancel_queue_item(11)
    assert result["status_code"] == 204


async def test_list_nodes(jenkins_client: JenkinsClient, httpx_mock) -> None:
    httpx_mock.add_response(
        url="http://jenkins.test/computer/api/json",
        json={"computer": [{"displayName": "built-in"}]},
    )
    result = await jenkins_client.list_nodes()
    assert result[0]["displayName"] == "built-in"


async def test_get_plugin_list(jenkins_client: JenkinsClient, httpx_mock) -> None:
    httpx_mock.add_response(
        url="http://jenkins.test/pluginManager/api/json?depth=1",
        json={"plugins": [{"shortName": "git"}]},
    )
    result = await jenkins_client.get_plugin_list()
    assert result[0]["shortName"] == "git"


# ------------------------------------------------------------------ errors
async def test_raises_authentication_error_on_401(
    jenkins_client: JenkinsClient, httpx_mock
) -> None:
    httpx_mock.add_response(
        url="http://jenkins.test/api/json?tree=jobs%5Bname%2Curl%2Ccolor%5D",
        status_code=401,
    )
    with pytest.raises(AuthenticationError):
        await jenkins_client.list_jobs()


async def test_raises_not_found_on_404(jenkins_client: JenkinsClient, httpx_mock) -> None:
    httpx_mock.add_response(
        url="http://jenkins.test/job/missing/api/json", status_code=404
    )
    with pytest.raises(NotFoundError):
        await jenkins_client.get_job("missing")


async def test_raises_api_error_on_500(jenkins_client: JenkinsClient, httpx_mock) -> None:
    httpx_mock.add_response(
        url="http://jenkins.test/job/demo/api/json",
        status_code=500,
        text="boom",
    )
    with pytest.raises(APIError) as info:
        await jenkins_client.get_job("demo")
    assert info.value.status_code == 500
