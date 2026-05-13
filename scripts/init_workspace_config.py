from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from workspace_config import (
    DEFAULT_BASE_URL,
    InvalidWorkspaceConfigError,
    WorkspaceConfigWriteError,
    build_workspace_config,
    write_workspace_files,
)


def _parse_bool(value: str) -> bool:
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"Invalid boolean value: {value!r}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Initialize wan2.7-image-demo workspace defaults."
    )
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    parser.add_argument("--api-key", help="Raw DashScope API key to store in api_key.txt.")
    parser.add_argument(
        "--model",
        default="wan2.7-image",
        help="Default model to save in workspace config.",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="Default DashScope base URL to save in workspace config.",
    )
    parser.add_argument("--t2i-size", required=True, help="Concrete pixel size, e.g. 1024*1024.")
    parser.add_argument("--t2i-n", required=True, type=int, help="Default t2i image count.")
    parser.add_argument(
        "--t2i-watermark",
        required=True,
        type=_parse_bool,
        help="Default t2i watermark toggle: true/false.",
    )
    parser.add_argument(
        "--t2i-thinking-mode",
        required=True,
        type=_parse_bool,
        help="Default t2i thinking_mode toggle: true/false.",
    )
    parser.add_argument("--i2i-size", required=True, help="Concrete pixel size, e.g. 1024*1024.")
    parser.add_argument("--i2i-n", required=True, type=int, help="Default i2i image count.")
    parser.add_argument(
        "--i2i-watermark",
        required=True,
        type=_parse_bool,
        help="Default i2i watermark toggle: true/false.",
    )
    parser.add_argument(
        "--video-t2v-model",
        default="wan2.6-t2v",
        help="Default text-to-video model.",
    )
    parser.add_argument(
        "--video-t2v-size",
        default="1280*720",
        help="Default text-to-video concrete size, e.g. 1280*720.",
    )
    parser.add_argument(
        "--video-t2v-duration",
        default=2,
        type=int,
        help="Default text-to-video duration in seconds.",
    )
    parser.add_argument(
        "--video-t2v-prompt-extend",
        default=True,
        type=_parse_bool,
        help="Default text-to-video prompt_extend toggle: true/false.",
    )
    parser.add_argument(
        "--video-t2v-watermark",
        default=False,
        type=_parse_bool,
        help="Default text-to-video watermark toggle: true/false.",
    )
    parser.add_argument(
        "--video-i2v-model",
        default="wan2.7-i2v",
        help="Default image-to-video model.",
    )
    parser.add_argument(
        "--video-i2v-resolution",
        default="720P",
        help="Default image-to-video resolution tier.",
    )
    parser.add_argument(
        "--video-i2v-duration",
        default=5,
        type=int,
        help="Default image-to-video duration in seconds.",
    )
    parser.add_argument(
        "--video-i2v-prompt-extend",
        default=True,
        type=_parse_bool,
        help="Default image-to-video prompt_extend toggle: true/false.",
    )
    parser.add_argument(
        "--video-i2v-watermark",
        default=False,
        type=_parse_bool,
        help="Default image-to-video watermark toggle: true/false.",
    )
    parser.add_argument(
        "--videoedit-model",
        default="wan2.7-videoedit",
        help="Default video editing model.",
    )
    parser.add_argument(
        "--videoedit-resolution",
        default="720P",
        help="Default video editing resolution tier.",
    )
    parser.add_argument(
        "--videoedit-duration",
        default=0,
        type=int,
        help="Default video editing duration. Use 0 to keep source duration.",
    )
    parser.add_argument(
        "--videoedit-prompt-extend",
        default=True,
        type=_parse_bool,
        help="Default video editing prompt_extend toggle: true/false.",
    )
    parser.add_argument(
        "--videoedit-watermark",
        default=False,
        type=_parse_bool,
        help="Default video editing watermark toggle: true/false.",
    )
    parser.add_argument(
        "--videoedit-audio-setting",
        default="origin",
        choices=["auto", "origin"],
        help="Default video editing audio setting.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing wan2.7-image-demo.json and api_key.txt if present.",
    )
    return parser.parse_args()


def _emit(summary: dict[str, Any], *, exit_code: int) -> None:
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    raise SystemExit(exit_code)


def main() -> None:
    args = _parse_args()
    workspace_root = args.workspace_root.resolve()

    try:
        config = build_workspace_config(
            model=args.model,
            base_url=args.base_url,
            t2i_size=args.t2i_size,
            t2i_n=args.t2i_n,
            t2i_watermark=args.t2i_watermark,
            t2i_thinking_mode=args.t2i_thinking_mode,
            i2i_size=args.i2i_size,
            i2i_n=args.i2i_n,
            i2i_watermark=args.i2i_watermark,
            video_t2v_model=args.video_t2v_model,
            video_t2v_size=args.video_t2v_size,
            video_t2v_duration=args.video_t2v_duration,
            video_t2v_prompt_extend=args.video_t2v_prompt_extend,
            video_t2v_watermark=args.video_t2v_watermark,
            video_i2v_model=args.video_i2v_model,
            video_i2v_resolution=args.video_i2v_resolution,
            video_i2v_duration=args.video_i2v_duration,
            video_i2v_prompt_extend=args.video_i2v_prompt_extend,
            video_i2v_watermark=args.video_i2v_watermark,
            videoedit_model=args.videoedit_model,
            videoedit_resolution=args.videoedit_resolution,
            videoedit_duration=args.videoedit_duration,
            videoedit_prompt_extend=args.videoedit_prompt_extend,
            videoedit_watermark=args.videoedit_watermark,
            videoedit_audio_setting=args.videoedit_audio_setting,
        )
        write_result = write_workspace_files(
            workspace_root,
            config=config,
            api_key=args.api_key,
            force=args.force,
        )
        _emit(
            {
                "status": "success",
                "workspace_root": str(workspace_root),
                "config": config,
                "config_file": write_result["config_file"],
                "api_key_file": write_result["api_key_file"],
            },
            exit_code=0,
        )
    except (
        InvalidWorkspaceConfigError,
        WorkspaceConfigWriteError,
        OSError,
    ) as exc:
        _emit(
            {
                "status": "error",
                "error": str(exc),
                "error_type": exc.__class__.__name__,
                "workspace_root": str(workspace_root),
            },
            exit_code=1,
        )


if __name__ == "__main__":
    main()
