from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any
from urllib import error, request


ASYNC_CREATE_ENDPOINT = "/services/aigc/image-generation/generation"
VIDEO_GENERATION_ENDPOINT = "/services/aigc/video-generation/video-synthesis"
IMAGE2VIDEO_ENDPOINT = "/services/aigc/image2video/video-synthesis"


class ApiTransportError(RuntimeError):
    """HTTP/API level failures."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_body: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body or {}

@dataclass(slots=True)
class TransportBundle:
    transport_used: str
    create_url: str
    create_response: dict[str, Any]
    final_response: dict[str, Any]
    poll_history: list[dict[str, Any]]


def _headers(api_key: str, *, async_mode: bool) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if async_mode:
        headers["X-DashScope-Async"] = "enable"
    return headers


def _json_request(
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    payload: dict[str, Any] | None,
    timeout: float,
) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(url=url, data=body, headers=headers, method=method.upper())
    try:
        with request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        parsed: dict[str, Any] | None = None
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = {"raw": raw}
        message = parsed.get("message") if isinstance(parsed, dict) else None
        raise ApiTransportError(
            message or f"HTTP {exc.code} from DashScope",
            status_code=exc.code,
            response_body=parsed if isinstance(parsed, dict) else {"raw": raw},
        ) from exc
    except error.URLError as exc:
        raise ApiTransportError(f"Network error while calling DashScope: {exc}") from exc


def _extract_task_id(response_data: dict[str, Any]) -> str | None:
    output = response_data.get("output", {})
    task_id = output.get("task_id")
    return str(task_id) if task_id else None

def _poll_task(
    *,
    api_key: str,
    base_url: str,
    task_id: str,
    timeout_seconds: float,
    poll_interval: float,
    request_timeout: float,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    deadline = time.monotonic() + timeout_seconds
    history: list[dict[str, Any]] = []
    task_url = f"{base_url}/tasks/{task_id}"

    while True:
        response_data = _json_request(
            "GET",
            task_url,
            headers=_headers(api_key, async_mode=False),
            payload=None,
            timeout=request_timeout,
        )
        history.append(response_data)
        output = response_data.get("output", {})
        task_status = str(output.get("task_status", "")).upper()

        if task_status in {"SUCCEEDED", "FAILED", "CANCELED"}:
            return response_data, history

        if time.monotonic() >= deadline:
            raise ApiTransportError(
                f"Timed out while waiting for task {task_id} after {timeout_seconds} seconds.",
                response_body=response_data,
            )

        time.sleep(poll_interval)


def execute_generation(
    *,
    payload: dict[str, Any],
    api_key: str,
    base_url: str,
    create_endpoint: str = ASYNC_CREATE_ENDPOINT,
    request_timeout: float,
    poll_timeout: float,
    poll_interval: float,
) -> TransportBundle:
    async_url = f"{base_url}{create_endpoint}"

    create_response = _json_request(
        "POST",
        async_url,
        headers=_headers(api_key, async_mode=True),
        payload=payload,
        timeout=request_timeout,
    )
    task_id = _extract_task_id(create_response)
    if not task_id:
        return TransportBundle(
            transport_used="async-single-response",
            create_url=async_url,
            create_response=create_response,
            final_response=create_response,
            poll_history=[],
        )

    final_response, poll_history = _poll_task(
        api_key=api_key,
        base_url=base_url,
        task_id=task_id,
        timeout_seconds=poll_timeout,
        poll_interval=poll_interval,
        request_timeout=request_timeout,
    )
    return TransportBundle(
        transport_used="async",
        create_url=async_url,
        create_response=create_response,
        final_response=final_response,
        poll_history=poll_history,
    )
