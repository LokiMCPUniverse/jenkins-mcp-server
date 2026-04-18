"""FastMCP server exposing Jenkins tools."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

from .client import JenkinsClient
from .config import JenkinsConfig


@dataclass
class AppContext:
    """Lifespan-scoped application context."""

    client: JenkinsClient
    config: JenkinsConfig


@asynccontextmanager
async def lifespan(_server: FastMCP) -> AsyncIterator[AppContext]:
    """Build the Jenkins client on startup and close it on shutdown."""
    config = JenkinsConfig()
    client = JenkinsClient(config)
    try:
        yield AppContext(client=client, config=config)
    finally:
        await client.aclose()


mcp = FastMCP(
    "jenkins-mcp",
    instructions=(
        "Tools for interacting with a Jenkins CI/CD controller: list/trigger "
        "jobs, fetch build status and console logs, manage the build queue, "
        "and inspect nodes and plugins."
    ),
    lifespan=lifespan,
)


def _client(ctx: Context) -> JenkinsClient:
    return ctx.request_context.lifespan_context.client


@mcp.tool()
async def list_jobs(ctx: Context, folder: str | None = None) -> list[dict[str, Any]]:
    """List Jenkins jobs. Optionally scoped to a folder path like ``team/app``."""
    return await _client(ctx).list_jobs(folder)


@mcp.tool()
async def get_job(ctx: Context, job_name: str) -> dict[str, Any]:
    """Return full job metadata for ``job_name`` (supports nested folder paths)."""
    return await _client(ctx).get_job(job_name)


@mcp.tool()
async def trigger_build(
    ctx: Context,
    job_name: str,
    parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Trigger a Jenkins build. Uses ``buildWithParameters`` when ``parameters`` is provided."""
    return await _client(ctx).trigger_build(job_name, parameters)


@mcp.tool()
async def get_build(ctx: Context, job_name: str, build_number: int) -> dict[str, Any]:
    """Return detailed information about a specific build."""
    return await _client(ctx).get_build(job_name, build_number)


@mcp.tool()
async def get_build_log(ctx: Context, job_name: str, build_number: int) -> str:
    """Return the plain-text console log for a build."""
    return await _client(ctx).get_build_log(job_name, build_number)


@mcp.tool()
async def stop_build(ctx: Context, job_name: str, build_number: int) -> dict[str, Any]:
    """Request cancellation of an in-progress build."""
    return await _client(ctx).stop_build(job_name, build_number)


@mcp.tool()
async def list_builds(
    ctx: Context, job_name: str, limit: int = 20
) -> list[dict[str, Any]]:
    """Return up to ``limit`` recent builds for ``job_name`` with result/timestamp/duration."""
    return await _client(ctx).list_builds(job_name, limit)


@mcp.tool()
async def list_queue(ctx: Context) -> list[dict[str, Any]]:
    """Return all items currently in the Jenkins build queue."""
    return await _client(ctx).list_queue()


@mcp.tool()
async def cancel_queue_item(ctx: Context, item_id: int) -> dict[str, Any]:
    """Cancel a queued build by its queue item id."""
    return await _client(ctx).cancel_queue_item(item_id)


@mcp.tool()
async def list_nodes(ctx: Context) -> list[dict[str, Any]]:
    """Return all known Jenkins nodes/agents (including the built-in controller)."""
    return await _client(ctx).list_nodes()


@mcp.tool()
async def get_plugin_list(ctx: Context) -> list[dict[str, Any]]:
    """Return all installed Jenkins plugins with metadata (depth=1)."""
    return await _client(ctx).get_plugin_list()


def main() -> None:
    """Entry point used by the ``jenkins-mcp`` console script."""
    mcp.run()


if __name__ == "__main__":
    main()
