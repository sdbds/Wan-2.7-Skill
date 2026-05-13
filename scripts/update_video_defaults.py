from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from workspace_config import (
    CONFIG_FILENAME,
    InvalidWorkspaceConfigError,
    build_video_defaults,
    load_workspace_config,
)

DEFAULT_VIDEO_KWARGS = {
    "video_t2v_model": "wan2.6-t2v",
    "video_t2v_size": "1280*720",
    "video_t2v_duration": 2,
    "video_t2v_prompt_extend": True,
    "video_t2v_watermark": False,
    "video_i2v_model": "wan2.7-i2v",
    "video_i2v_resolution": "720P",
    "video_i2v_duration": 5,
    "video_i2v_prompt_extend": True,
    "video_i2v_watermark": False,
    "videoedit_model": "wan2.7-videoedit",
    "videoedit_resolution": "720P",
    "videoedit_duration": 0,
    "videoedit_prompt_extend": True,
    "videoedit_watermark": False,
    "videoedit_audio_setting": "origin",
}

ARG_TO_KWARG = {
    "video_t2v_model": ("t2v", "model"),
    "video_t2v_size": ("t2v", "size"),
    "video_t2v_duration": ("t2v", "duration"),
    "video_t2v_prompt_extend": ("t2v", "prompt_extend"),
    "video_t2v_watermark": ("t2v", "watermark"),
    "video_i2v_model": ("i2v", "model"),
    "video_i2v_resolution": ("i2v", "resolution"),
    "video_i2v_duration": ("i2v", "duration"),
    "video_i2v_prompt_extend": ("i2v", "prompt_extend"),
    "video_i2v_watermark": ("i2v", "watermark"),
    "videoedit_model": ("videoedit", "model"),
    "videoedit_resolution": ("videoedit", "resolution"),
    "videoedit_duration": ("videoedit", "duration"),
    "videoedit_prompt_extend": ("videoedit", "prompt_extend"),
    "videoedit_watermark": ("videoedit", "watermark"),
    "videoedit_audio_setting": ("videoedit", "audio_setting"),
}


def _parse_bool(value: str) -> bool:
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"Invalid boolean value: {value!r}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add or update video defaults in wan2.7-image-demo workspace config."
    )
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Replace the whole defaults.video block instead of merging explicit fields.",
    )
    parser.add_argument("--video-t2v-model")
    parser.add_argument("--video-t2v-size")
    parser.add_argument("--video-t2v-duration", type=int)
    parser.add_argument("--video-t2v-prompt-extend", type=_parse_bool)
    parser.add_argument("--video-t2v-watermark", type=_parse_bool)
    parser.add_argument("--video-i2v-model")
    parser.add_argument("--video-i2v-resolution")
    parser.add_argument("--video-i2v-duration", type=int)
    parser.add_argument("--video-i2v-prompt-extend", type=_parse_bool)
    parser.add_argument("--video-i2v-watermark", type=_parse_bool)
    parser.add_argument("--videoedit-model")
    parser.add_argument("--videoedit-resolution")
    parser.add_argument("--videoedit-duration", type=int)
    parser.add_argument("--videoedit-prompt-extend", type=_parse_bool)
    parser.add_argument("--videoedit-watermark", type=_parse_bool)
    parser.add_argument(
        "--videoedit-audio-setting",
        choices=["auto", "origin"],
    )
    return parser.parse_args()


def _emit(summary: dict[str, Any], *, exit_code: int) -> None:
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    raise SystemExit(exit_code)


def _kwargs_from_existing_video_defaults(value: Any) -> dict[str, Any]:
    kwargs = dict(DEFAULT_VIDEO_KWARGS)
    if not isinstance(value, dict):
        return kwargs

    for kwarg_name, (section_name, field_name) in ARG_TO_KWARG.items():
        section = value.get(section_name)
        if isinstance(section, dict) and field_name in section:
            kwargs[kwarg_name] = section[field_name]
    return kwargs


def _explicit_video_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    return {
        key: value
        for key, value in vars(args).items()
        if key in ARG_TO_KWARG and value is not None
    }


def main() -> None:
    args = _parse_args()
    workspace_root = args.workspace_root.resolve()
    config_path = workspace_root / CONFIG_FILENAME

    try:
        config, config_source = load_workspace_config(workspace_root)
        if config_source is None:
            raise InvalidWorkspaceConfigError(
                f"{CONFIG_FILENAME} does not exist. Run init_workspace_config.py first."
            )

        defaults = config.setdefault("defaults", {})
        if not isinstance(defaults, dict):
            raise InvalidWorkspaceConfigError("'defaults' must be an object.")

        if args.reset:
            video_kwargs = dict(DEFAULT_VIDEO_KWARGS)
        else:
            video_kwargs = _kwargs_from_existing_video_defaults(defaults.get("video"))
        video_kwargs.update(_explicit_video_kwargs(args))

        video_defaults = build_video_defaults(**video_kwargs)
        defaults["video"] = video_defaults
        config_path.write_text(
            json.dumps(config, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        _emit(
            {
                "status": "success",
                "workspace_root": str(workspace_root),
                "config_file": str(config_path),
                "video_defaults": video_defaults,
            },
            exit_code=0,
        )
    except (InvalidWorkspaceConfigError, OSError, json.JSONDecodeError) as exc:
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
