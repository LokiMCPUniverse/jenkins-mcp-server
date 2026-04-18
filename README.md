# Jenkins MCP Server

A Model Context Protocol (MCP) server that exposes a Jenkins controller's REST
API to MCP-compatible clients such as Claude Desktop. Built on the
[MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) (1.27+,
protocol 2025-11-25) using `FastMCP` with `httpx` for async HTTP and
`pydantic-settings` for configuration.

## Features

- HTTP basic authentication using a Jenkins username + API token
- Automatic CSRF crumb fetch and cache for POST requests
- Works with nested folder job paths (`team/app/main`)
- Tools for jobs, builds, console logs, queue, nodes and plugins

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Configuration

All configuration is read from environment variables prefixed with `JENKINS_`.

| Variable              | Default                  | Description                              |
|-----------------------|--------------------------|------------------------------------------|
| `JENKINS_BASE_URL`    | `http://localhost:8080`  | Base URL of the Jenkins controller       |
| `JENKINS_USERNAME`    | *(empty)*                | Jenkins user for HTTP basic auth         |
| `JENKINS_API_TOKEN`   | *(empty)*                | Jenkins API token (create in user settings) |
| `JENKINS_VERIFY_SSL`  | `true`                   | Verify TLS certificates                  |
| `JENKINS_TIMEOUT`     | `30`                     | HTTP timeout in seconds                  |

A `.env` file in the working directory is also picked up automatically.

## Running

```bash
jenkins-mcp
```

## Claude Desktop configuration

Add an entry to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "jenkins": {
      "command": "jenkins-mcp",
      "env": {
        "JENKINS_BASE_URL": "https://jenkins.example.com",
        "JENKINS_USERNAME": "your-username",
        "JENKINS_API_TOKEN": "your-api-token"
      }
    }
  }
}
```

## Tools

| Tool                 | Description                                                |
|----------------------|------------------------------------------------------------|
| `list_jobs`          | List jobs (optionally scoped to a folder)                  |
| `get_job`            | Return full job metadata                                   |
| `trigger_build`      | Trigger a build, optionally with parameters                |
| `get_build`          | Return metadata for a specific build                       |
| `get_build_log`      | Fetch the console text for a build                         |
| `stop_build`         | Stop a running build                                       |
| `list_builds`        | List recent builds (`limit` defaults to 20)                |
| `list_queue`         | List queued build items                                    |
| `cancel_queue_item`  | Cancel a queue item by id                                  |
| `list_nodes`         | List Jenkins nodes / agents                                |
| `get_plugin_list`    | List installed Jenkins plugins                             |

## Development

Run tests with:

```bash
pytest -x --tb=short
```

Lint with:

```bash
ruff check src tests
```
