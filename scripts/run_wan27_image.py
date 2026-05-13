from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from build_request import InvalidJobSpecError, build_request_payload, load_job_spec
from call_api import ApiTransportError, execute_generation
from download_images import download_images
from normalize_response import normalize_generation_result
from read_api_key import ApiKeyNotFoundError, load_api_key
from workspace_config import (
    InvalidWorkspaceConfigError,
    load_workspace_config,
    resolve_default_base_url,
)


def _timestamp_slug() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H-%M-%S")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a wan2.7-image generation job.")
    parser.add_argument("--prompt", help="Prompt text.")
    parser.add_argument("--image", action="append", help="Local image path or public URL.")
    parser.add_argument("--spec-file", type=Path, help="JSON file with prompt/images/parameters.")
    parser.add_argument(
        "--model",
        help="Model name: wan2.7-image or wan2.7-image-pro.",
    )
    parser.add_argument("--size", help="1K/2K/4K or WIDTH*HEIGHT.")
    parser.add_argument("--n", type=int, help="Number of images to request.")
    parser.add_argument("--seed", type=int, help="Optional random seed.")
    parser.add_argument("--watermark", help="true/false")
    parser.add_argument("--enable-sequential", help="true/false")
    parser.add_argument("--thinking-mode", help="true/false")
    parser.add_argument(
        "--color-palette-file",
        type=Path,
        help="JSON file containing the color_palette array.",
    )
    parser.add_argument(
        "--bbox-file",
        type=Path,
        help="JSON file containing the bbox_list array.",
    )
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-root", type=Path)
    parser.add_argument(
        "--base-url",
        help="DashScope base URL. Beijing default is used unless overridden.",
    )
    parser.add_argument("--request-timeout", type=float, default=90.0)
    parser.add_argument("--poll-timeout", type=float, default=120.0)
    parser.add_argument("--poll-interval", type=float, default=2.0)
    return parser.parse_args()


def _parameters_from_args(args: argparse.Namespace) -> dict[str, Any]:
    mapping = {
        "size": args.size,
        "n": args.n,
        "seed": args.seed,
        "watermark": args.watermark,
        "enable_sequential": args.enable_sequential,
        "thinking_mode": args.thinking_mode,
    }
    parameters = {key: value for key, value in mapping.items() if value is not None}
    if args.color_palette_file is not None:
        parameters["color_palette"] = json.loads(
            args.color_palette_file.read_text(encoding="utf-8")
        )
    if args.bbox_file is not None:
        parameters["bbox_list"] = json.loads(
            args.bbox_file.read_text(encoding="utf-8")
        )
    return parameters


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
        else workspace_root / "outputs" / "wan2.7-image-demo" / _timestamp_slug()
    )
    output_root.mkdir(parents=True, exist_ok=True)

    error_path = output_root / "error.json"

    try:
        workspace_config, workspace_config_source = load_workspace_config(workspace_root)
        job = load_job_spec(
            spec_file=args.spec_file.resolve() if args.spec_file else None,
            prompt=args.prompt,
            images=args.image,
            parameters=_parameters_from_args(args),
            model=args.model,
            workspace_root=workspace_root,
            workspace_config=workspace_config,
        )

        api_key, api_key_source = load_api_key(workspace_root)
        base_url = resolve_default_base_url(workspace_config)
        if args.base_url:
            base_url = args.base_url.strip()
        payload, warnings = build_request_payload(job)
        _write_json(output_root / "request.json", payload)

        transport_bundle = execute_generation(
            payload=payload,
            api_key=api_key,
            base_url=base_url.rstrip("/"),
            request_timeout=args.request_timeout,
            poll_timeout=args.poll_timeout,
            poll_interval=args.poll_interval,
        )
        _write_json(output_root / "response.create.json", transport_bundle.create_response)
        _write_json(output_root / "response.final.json", transport_bundle.final_response)
        if transport_bundle.poll_history:
            _write_json(output_root / "response.poll-history.json", transport_bundle.poll_history)

        normalized = normalize_generation_result(transport_bundle.final_response)
        local_images, download_failures = download_images(
            normalized["remote_images"],
            output_dir=output_root,
            timeout=args.request_timeout,
        )

        status = "success" if local_images else "error"
        if local_images and (normalized["result_failures"] or download_failures):
            status = "partial"

        summary = {
            "status": status,
            "mode": job.mode,
            "model": job.model,
            "prompt": job.prompt,
            "input_images": job.images,
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
            "remote_images": normalized["remote_images"],
            "local_images": local_images,
            "warnings": warnings,
            "result_failures": normalized["result_failures"],
            "download_failures": download_failures,
            "usage": normalized["usage"],
        }
        _write_json(output_root / "summary.json", summary)
        _emit_and_exit(summary, exit_code=0 if local_images else 1)

    except (
        ApiKeyNotFoundError,
        InvalidJobSpecError,
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
