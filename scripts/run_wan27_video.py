from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from build_video_request import (
    InvalidVideoSpecError,
    build_video_request_payload,
    load_video_job_spec,
)
from call_api import ApiTransportError, execute_generation
from download_media import download_urls
from normalize_video_response import normalize_video_result
from read_api_key import ApiKeyNotFoundError, load_api_key
from workspace_config import (
    InvalidWorkspaceConfigError,
    load_workspace_config,
    resolve_default_base_url,
)


def _timestamp_slug() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H-%M-%S")


def _parse_bool(value: str) -> bool:
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"Invalid boolean value: {value!r}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a Wan video generation job.")
    parser.add_argument("--prompt", help="Video prompt text.")
    parser.add_argument("--spec-file", type=Path, help="JSON file with model/input/parameters.")
    parser.add_argument("--model", help="Video model name, e.g. wan2.7-i2v.")
    parser.add_argument(
        "--endpoint",
        choices=["video-generation", "image2video"],
        help="Create endpoint family. Defaults to video-generation.",
    )
    parser.add_argument(
        "--media",
        action="append",
        help="Video media item as TYPE=URL, e.g. first_frame=https://... or video=https://...",
    )
    parser.add_argument("--resolution", help="Resolution tier, e.g. 720P or 1080P.")
    parser.add_argument("--size", help="Concrete video size, e.g. 1280*720.")
    parser.add_argument("--ratio", help="Output aspect ratio for models that support it.")
    parser.add_argument("--duration", type=int, help="Video duration in seconds.")
    parser.add_argument("--prompt-extend", type=_parse_bool, help="true/false")
    parser.add_argument("--watermark", type=_parse_bool, help="true/false")
    parser.add_argument("--seed", type=int, help="Optional random seed.")
    parser.add_argument("--shot-type", choices=["single", "multi"], help="single/multi")
    parser.add_argument("--audio", type=_parse_bool, help="Audio toggle for models that support it.")
    parser.add_argument("--audio-setting", choices=["auto", "origin"], help="Audio setting.")
    parser.add_argument("--negative-prompt", help="Optional negative prompt.")
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-root", type=Path)
    parser.add_argument(
        "--base-url",
        help="DashScope base URL. Workspace default or Beijing default is used unless overridden.",
    )
    parser.add_argument("--request-timeout", type=float, default=90.0)
    parser.add_argument("--poll-timeout", type=float, default=600.0)
    parser.add_argument("--poll-interval", type=float, default=15.0)
    return parser.parse_args()


def _parameters_from_args(args: argparse.Namespace) -> dict[str, Any]:
    mapping = {
        "resolution": args.resolution,
        "size": args.size,
        "ratio": args.ratio,
        "duration": args.duration,
        "prompt_extend": args.prompt_extend,
        "watermark": args.watermark,
        "seed": args.seed,
        "shot_type": args.shot_type,
        "audio": args.audio,
        "audio_setting": args.audio_setting,
    }
    return {key: value for key, value in mapping.items() if value is not None}


def _input_overrides_from_args(args: argparse.Namespace) -> dict[str, Any]:
    mapping = {
        "negative_prompt": args.negative_prompt,
    }
    return {key: value for key, value in mapping.items() if value is not None}


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _emit_and_exit(summary: dict[str, Any], *, exit_code: int) -> None:
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    raise SystemExit(exit_code)


def main() -> None:
    args = _parse_args()
    workspace_root = args.workspace_root.resolve()
    output_root = (
        args.output_root.resolve()
        if args.output_root
        else workspace_root / "outputs" / "wan-2.7" / "video" / _timestamp_slug()
    )
    output_root.mkdir(parents=True, exist_ok=True)

    error_path = output_root / "error.json"

    try:
        workspace_config, workspace_config_source = load_workspace_config(workspace_root)
        job = load_video_job_spec(
            spec_file=args.spec_file.resolve() if args.spec_file else None,
            prompt=args.prompt,
            media=args.media,
            input_overrides=_input_overrides_from_args(args),
            parameters=_parameters_from_args(args),
            model=args.model,
            endpoint=args.endpoint,
            workspace_root=workspace_root,
            workspace_config=workspace_config,
        )

        api_key, api_key_source = load_api_key(workspace_root)
        base_url = args.base_url.strip() if args.base_url else resolve_default_base_url(workspace_config)
        payload = build_video_request_payload(job)
        _write_json(output_root / "request.json", payload)

        transport_bundle = execute_generation(
            payload=payload,
            api_key=api_key,
            base_url=base_url.rstrip("/"),
            create_endpoint=job.endpoint,
            request_timeout=args.request_timeout,
            poll_timeout=args.poll_timeout,
            poll_interval=args.poll_interval,
        )
        _write_json(output_root / "response.create.json", transport_bundle.create_response)
        _write_json(output_root / "response.final.json", transport_bundle.final_response)
        if transport_bundle.poll_history:
            _write_json(output_root / "response.poll-history.json", transport_bundle.poll_history)

        normalized = normalize_video_result(transport_bundle.final_response)
        local_videos, download_failures = download_urls(
            normalized["remote_videos"],
            output_dir=output_root,
            stem="video",
            default_extension=".mp4",
            timeout=args.request_timeout,
        )

        status = "success" if local_videos else "error"
        if local_videos and (normalized["result_failures"] or download_failures):
            status = "partial"

        summary = {
            "status": status,
            "model": job.model,
            "input": job.input,
            "parameters": job.parameters,
            "endpoint": job.endpoint,
            "transport_used": transport_bundle.transport_used,
            "api_key_source": api_key_source,
            "workspace_config_source": workspace_config_source,
            "base_url": base_url,
            "output_dir": str(output_root.resolve()),
            "request_file": str((output_root / "request.json").resolve()),
            "response_create_file": str((output_root / "response.create.json").resolve()),
            "response_final_file": str((output_root / "response.final.json").resolve()),
            "poll_history_file": str((output_root / "response.poll-history.json").resolve())
            if transport_bundle.poll_history
            else None,
            "request_id": normalized["request_id"],
            "task_id": normalized["task_id"],
            "task_status": normalized["task_status"],
            "error_code": normalized["error_code"],
            "error_message": normalized["error_message"],
            "remote_videos": normalized["remote_videos"],
            "local_videos": local_videos,
            "result_failures": normalized["result_failures"],
            "download_failures": download_failures,
            "usage": normalized["usage"],
        }
        _write_json(output_root / "summary.json", summary)
        _emit_and_exit(summary, exit_code=0 if local_videos else 1)

    except (
        ApiKeyNotFoundError,
        InvalidVideoSpecError,
        InvalidWorkspaceConfigError,
        ApiTransportError,
        OSError,
        json.JSONDecodeError,
    ) as exc:
        summary = {
            "status": "error",
            "error": str(exc),
            "error_type": exc.__class__.__name__,
            "output_dir": str(output_root.resolve()),
            "error_file": str(error_path.resolve()),
        }
        _write_json(error_path, summary)
        _emit_and_exit(summary, exit_code=1)


if __name__ == "__main__":
    main()
