from __future__ import annotations

from typing import Any


def _extract_choice_images(output: dict[str, Any]) -> list[str]:
    images: list[str] = []
    for choice in output.get("choices", []) or []:
        message = (choice or {}).get("message", {})
        for item in message.get("content", []) or []:
            image_value = item.get("image")
            if isinstance(image_value, str) and image_value:
                images.append(image_value)
            elif isinstance(image_value, list):
                images.extend(str(entry) for entry in image_value if entry)
    return images


def _extract_result_images(output: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
    images: list[str] = []
    failures: list[dict[str, Any]] = []
    for item in output.get("results", []) or []:
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        if isinstance(url, str) and url:
            images.append(url)
            continue
        if item.get("code") or item.get("message"):
            failures.append(
                {
                    "code": item.get("code"),
                    "message": item.get("message"),
                }
            )
    return images, failures


def normalize_generation_result(response_data: dict[str, Any]) -> dict[str, Any]:
    output = response_data.get("output", {}) or {}
    usage = response_data.get("usage", {}) or {}
    request_id = response_data.get("request_id")
    task_id = output.get("task_id")
    task_status = output.get("task_status")
    error_code = response_data.get("code") or output.get("code")
    error_message = response_data.get("message") or output.get("message")

    choice_images = _extract_choice_images(output)
    result_images, result_failures = _extract_result_images(output)
    if error_code or error_message:
        result_failures = [
            {
                "code": error_code,
                "message": error_message,
            },
            *result_failures,
        ]
    remote_images = choice_images or result_images

    summary = {
        "request_id": request_id,
        "task_id": task_id,
        "task_status": task_status,
        "error_code": error_code,
        "error_message": error_message,
        "remote_images": remote_images,
        "result_failures": result_failures,
        "usage": usage,
        "raw_output": output,
    }
    return summary
