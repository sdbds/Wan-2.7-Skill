from __future__ import annotations

from typing import Any


def normalize_video_result(response_data: dict[str, Any]) -> dict[str, Any]:
    output = response_data.get("output", {}) or {}
    usage = response_data.get("usage", {}) or {}
    request_id = response_data.get("request_id")
    task_id = output.get("task_id")
    task_status = output.get("task_status")
    error_code = response_data.get("code") or output.get("code")
    error_message = response_data.get("message") or output.get("message")

    video_url = output.get("video_url")
    remote_videos = [video_url] if isinstance(video_url, str) and video_url else []
    result_failures: list[dict[str, Any]] = []
    if error_code or error_message:
        result_failures.append({"code": error_code, "message": error_message})

    return {
        "request_id": request_id,
        "task_id": task_id,
        "task_status": task_status,
        "error_code": error_code,
        "error_message": error_message,
        "remote_videos": remote_videos,
        "result_failures": result_failures,
        "usage": usage,
        "raw_output": output,
    }
