"""Smoke tests for the FastMCP server wiring."""

from __future__ import annotations

from jenkins_mcp import server as server_module
from jenkins_mcp.server import mcp


async def test_server_exposes_expected_tools() -> None:
    tools = await mcp.list_tools()
    names = {tool.name for tool in tools}
    expected = {
        "list_jobs",
        "get_job",
        "trigger_build",
        "get_build",
        "get_build_log",
        "stop_build",
        "list_builds",
        "list_queue",
        "cancel_queue_item",
        "list_nodes",
        "get_plugin_list",
    }
    assert expected <= names


def test_main_entrypoint_exists() -> None:
    assert callable(server_module.main)
