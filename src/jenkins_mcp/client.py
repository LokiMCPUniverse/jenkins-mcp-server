"""Asynchronous Jenkins REST API client."""

from __future__ import annotations

from typing import Any

import httpx

from .config import JenkinsConfig
from .exceptions import APIError, AuthenticationError, NotFoundError


class JenkinsClient:
    """Thin async wrapper around the Jenkins JSON REST API.

    Handles HTTP basic authentication and caches the CSRF crumb required for
    POST requests against Jenkins instances that have CSRF protection enabled.
    """

    def __init__(self, config: JenkinsConfig, http_client: httpx.AsyncClient | None = None) -> None:
        self.config = config
        self._owns_client = http_client is None
        if http_client is None:
            auth: httpx.BasicAuth | None = None
            if config.username and config.api_token:
                auth = httpx.BasicAuth(config.username, config.api_token)
            http_client = httpx.AsyncClient(
                base_url=config.normalized_base_url,
                auth=auth,
                timeout=config.timeout,
                verify=config.verify_ssl,
            )
        self._client = http_client
        self._crumb_cache: dict[str, str] | None = None

    async def aclose(self) -> None:
        """Close the underlying httpx client if this instance owns it."""
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> JenkinsClient:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    # ------------------------------------------------------------------ crumb
    async def _crumb(self) -> dict[str, str]:
        """Fetch and cache the Jenkins CSRF crumb header.

        If the Jenkins instance does not enforce CSRF (older installs), the
        ``/crumbIssuer/api/json`` endpoint returns 404 - in that case we cache
        an empty mapping and skip crumb injection on subsequent POSTs.
        """
        if self._crumb_cache is not None:
            return self._crumb_cache

        try:
            response = await self._client.get("/crumbIssuer/api/json")
        except httpx.HTTPError as exc:
            raise APIError(f"Failed to fetch CSRF crumb: {exc}") from exc

        if response.status_code == 404:
            self._crumb_cache = {}
            return self._crumb_cache
        if response.status_code in (401, 403):
            raise AuthenticationError("Jenkins rejected credentials when fetching CSRF crumb")
        if response.status_code >= 400:
            raise APIError(
                f"Unexpected status {response.status_code} from crumb issuer",
                status_code=response.status_code,
            )

        payload = response.json()
        field = payload.get("crumbRequestField")
        crumb = payload.get("crumb")
        if not field or not crumb:
            self._crumb_cache = {}
        else:
            self._crumb_cache = {field: crumb}
        return self._crumb_cache

    # ---------------------------------------------------------- http helpers
    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        if response.status_code in (401, 403):
            raise AuthenticationError(
                f"Jenkins authentication failed ({response.status_code}) for {response.request.url}"
            )
        if response.status_code == 404:
            raise NotFoundError(f"Jenkins resource not found: {response.request.url}")
        raise APIError(
            f"Jenkins API error {response.status_code} for {response.request.url}: "
            f"{response.text[:500]}",
            status_code=response.status_code,
        )

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> httpx.Response:
        response = await self._client.get(path, params=params)
        self._raise_for_status(response)
        return response

    async def _post(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> httpx.Response:
        headers = await self._crumb()
        response = await self._client.post(path, params=params, data=data, headers=headers)
        self._raise_for_status(response)
        return response

    @staticmethod
    def _job_path(job_name: str) -> str:
        """Build the path segment for a (possibly nested) Jenkins job.

        ``folder/subfolder/job`` becomes ``/job/folder/job/subfolder/job/job``.
        """
        parts = [segment for segment in job_name.split("/") if segment]
        return "/" + "/".join(f"job/{segment}" for segment in parts)

    # --------------------------------------------------------------- jobs
    async def list_jobs(self, folder: str | None = None) -> list[dict[str, Any]]:
        prefix = self._job_path(folder) if folder else ""
        path = f"{prefix}/api/json" if prefix else "/api/json"
        response = await self._get(path, params={"tree": "jobs[name,url,color]"})
        return response.json().get("jobs", [])

    async def get_job(self, job_name: str) -> dict[str, Any]:
        response = await self._get(f"{self._job_path(job_name)}/api/json")
        return response.json()

    async def trigger_build(
        self, job_name: str, parameters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        base = self._job_path(job_name)
        if parameters:
            response = await self._post(f"{base}/buildWithParameters", data=parameters)
        else:
            response = await self._post(f"{base}/build")
        return {
            "status_code": response.status_code,
            "queue_location": response.headers.get("Location"),
        }

    async def get_build(self, job_name: str, build_number: int) -> dict[str, Any]:
        response = await self._get(f"{self._job_path(job_name)}/{build_number}/api/json")
        return response.json()

    async def get_build_log(self, job_name: str, build_number: int) -> str:
        response = await self._get(f"{self._job_path(job_name)}/{build_number}/consoleText")
        return response.text

    async def stop_build(self, job_name: str, build_number: int) -> dict[str, Any]:
        response = await self._post(f"{self._job_path(job_name)}/{build_number}/stop")
        return {"status_code": response.status_code}

    async def list_builds(self, job_name: str, limit: int = 20) -> list[dict[str, Any]]:
        tree = f"builds[number,result,timestamp,duration]{{0,{max(0, int(limit))}}}"
        response = await self._get(f"{self._job_path(job_name)}/api/json", params={"tree": tree})
        return response.json().get("builds", [])

    # --------------------------------------------------------------- queue
    async def list_queue(self) -> list[dict[str, Any]]:
        response = await self._get("/queue/api/json")
        return response.json().get("items", [])

    async def cancel_queue_item(self, item_id: int) -> dict[str, Any]:
        response = await self._post("/queue/cancelItem", params={"id": item_id})
        return {"status_code": response.status_code}

    # --------------------------------------------------------------- nodes
    async def list_nodes(self) -> list[dict[str, Any]]:
        response = await self._get("/computer/api/json")
        return response.json().get("computer", [])

    # ------------------------------------------------------------- plugins
    async def get_plugin_list(self) -> list[dict[str, Any]]:
        response = await self._get("/pluginManager/api/json", params={"depth": 1})
        return response.json().get("plugins", [])
