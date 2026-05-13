from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


CONFIG_FILENAME = "wan2.7-image-demo.json"
DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/api/v1"
API_KEY_FILENAME = "api_key.txt"
PIXEL_SIZE_PATTERN = re.compile(r"^\d{3,5}\*\d{3,5}$")
SUPPORTED_MODELS = {"wan2.7-image", "wan2.7-image-pro"}
SUPPORTED_VIDEO_MODELS = {
    "wan2.5-t2v-preview",
    "wan2.6-t2v",
    "wan2.7-i2v",
    "wan2.7-videoedit",
}
SUPPORTED_VIDEO_RESOLUTIONS = {"720P", "1080P"}
SUPPORTED_AUDIO_SETTINGS = {"auto", "origin"}


class InvalidWorkspaceConfigError(ValueError):
    """Raised when the workspace config file is malformed."""


class WorkspaceConfigWriteError(RuntimeError):
    """Raised when workspace config files cannot be written safely."""


def _normalize_model(value: str) -> str:
    normalized = str(value).strip()
    if normalized not in SUPPORTED_MODELS:
        raise InvalidWorkspaceConfigError(
            f"Unsupported model: {normalized!r}. Supported: {', '.join(sorted(SUPPORTED_MODELS))}"
        )
    return normalized


def _normalize_video_model(value: str, *, field_name: str) -> str:
    normalized = str(value).strip()
    if normalized not in SUPPORTED_VIDEO_MODELS:
        raise InvalidWorkspaceConfigError(
            f"Unsupported {field_name}: {normalized!r}. "
            f"Supported: {', '.join(sorted(SUPPORTED_VIDEO_MODELS))}"
        )
    return normalized


def _normalize_video_resolution(value: str, *, field_name: str) -> str:
    normalized = str(value).strip().upper()
    if normalized not in SUPPORTED_VIDEO_RESOLUTIONS:
        raise InvalidWorkspaceConfigError(
            f"{field_name} must be one of {', '.join(sorted(SUPPORTED_VIDEO_RESOLUTIONS))}."
        )
    return normalized


def _normalize_audio_setting(value: str, *, field_name: str) -> str:
    normalized = str(value).strip().lower()
    if normalized not in SUPPORTED_AUDIO_SETTINGS:
        raise InvalidWorkspaceConfigError(
            f"{field_name} must be one of {', '.join(sorted(SUPPORTED_AUDIO_SETTINGS))}."
        )
    return normalized


def _normalize_pixel_size(value: str, *, field_name: str) -> str:
    normalized = str(value).strip().upper()
    if not PIXEL_SIZE_PATTERN.fullmatch(normalized):
        raise InvalidWorkspaceConfigError(
            f"{field_name} must be a concrete pixel size like 1024*1024."
        )
    return normalized


def _normalize_non_negative_int(value: int, *, field_name: str) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError) as exc:
        raise InvalidWorkspaceConfigError(f"{field_name} must be an integer.") from exc
    if normalized < 0:
        raise InvalidWorkspaceConfigError(f"{field_name} must be non-negative.")
    return normalized


def _normalize_positive_int(value: int, *, field_name: str) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError) as exc:
        raise InvalidWorkspaceConfigError(f"{field_name} must be an integer.") from exc
    if normalized < 1:
        raise InvalidWorkspaceConfigError(f"{field_name} must be at least 1.")
    return normalized


def build_video_defaults(
    *,
    video_t2v_model: str = "wan2.6-t2v",
    video_t2v_size: str = "1280*720",
    video_t2v_duration: int = 2,
    video_t2v_prompt_extend: bool = True,
    video_t2v_watermark: bool = False,
    video_i2v_model: str = "wan2.7-i2v",
    video_i2v_resolution: str = "720P",
    video_i2v_duration: int = 5,
    video_i2v_prompt_extend: bool = True,
    video_i2v_watermark: bool = False,
    videoedit_model: str = "wan2.7-videoedit",
    videoedit_resolution: str = "720P",
    videoedit_duration: int = 0,
    videoedit_prompt_extend: bool = True,
    videoedit_watermark: bool = False,
    videoedit_audio_setting: str = "origin",
) -> dict[str, Any]:
    return {
        "t2v": {
            "model": _normalize_video_model(
                video_t2v_model, field_name="video_t2v_model"
            ),
            "size": _normalize_pixel_size(
                video_t2v_size, field_name="video_t2v_size"
            ),
            "duration": _normalize_positive_int(
                video_t2v_duration, field_name="video_t2v_duration"
            ),
            "prompt_extend": bool(video_t2v_prompt_extend),
            "watermark": bool(video_t2v_watermark),
        },
        "i2v": {
            "model": _normalize_video_model(
                video_i2v_model, field_name="video_i2v_model"
            ),
            "resolution": _normalize_video_resolution(
                video_i2v_resolution, field_name="video_i2v_resolution"
            ),
            "duration": _normalize_positive_int(
                video_i2v_duration, field_name="video_i2v_duration"
            ),
            "prompt_extend": bool(video_i2v_prompt_extend),
            "watermark": bool(video_i2v_watermark),
        },
        "videoedit": {
            "model": _normalize_video_model(
                videoedit_model, field_name="videoedit_model"
            ),
            "resolution": _normalize_video_resolution(
                videoedit_resolution, field_name="videoedit_resolution"
            ),
            "duration": _normalize_non_negative_int(
                videoedit_duration, field_name="videoedit_duration"
            ),
            "prompt_extend": bool(videoedit_prompt_extend),
            "watermark": bool(videoedit_watermark),
            "audio_setting": _normalize_audio_setting(
                videoedit_audio_setting, field_name="videoedit_audio_setting"
            ),
        },
    }


def build_workspace_config(
    *,
    model: str,
    base_url: str,
    t2i_size: str,
    t2i_n: int,
    t2i_watermark: bool,
    t2i_thinking_mode: bool,
    i2i_size: str,
    i2i_n: int,
    i2i_watermark: bool,
    video_t2v_model: str = "wan2.6-t2v",
    video_t2v_size: str = "1280*720",
    video_t2v_duration: int = 2,
    video_t2v_prompt_extend: bool = True,
    video_t2v_watermark: bool = False,
    video_i2v_model: str = "wan2.7-i2v",
    video_i2v_resolution: str = "720P",
    video_i2v_duration: int = 5,
    video_i2v_prompt_extend: bool = True,
    video_i2v_watermark: bool = False,
    videoedit_model: str = "wan2.7-videoedit",
    videoedit_resolution: str = "720P",
    videoedit_duration: int = 0,
    videoedit_prompt_extend: bool = True,
    videoedit_watermark: bool = False,
    videoedit_audio_setting: str = "origin",
) -> dict[str, Any]:
    normalized_base_url = str(base_url).strip() or DEFAULT_BASE_URL
    return {
        "model": _normalize_model(model),
        "base_url": normalized_base_url,
        "defaults": {
            "t2i": {
                "size": _normalize_pixel_size(t2i_size, field_name="t2i_size"),
                "n": _normalize_positive_int(t2i_n, field_name="t2i_n"),
                "watermark": bool(t2i_watermark),
                "thinking_mode": bool(t2i_thinking_mode),
            },
            "i2i": {
                "size": _normalize_pixel_size(i2i_size, field_name="i2i_size"),
                "n": _normalize_positive_int(i2i_n, field_name="i2i_n"),
                "watermark": bool(i2i_watermark),
            },
            "video": build_video_defaults(
                video_t2v_model=video_t2v_model,
                video_t2v_size=video_t2v_size,
                video_t2v_duration=video_t2v_duration,
                video_t2v_prompt_extend=video_t2v_prompt_extend,
                video_t2v_watermark=video_t2v_watermark,
                video_i2v_model=video_i2v_model,
                video_i2v_resolution=video_i2v_resolution,
                video_i2v_duration=video_i2v_duration,
                video_i2v_prompt_extend=video_i2v_prompt_extend,
                video_i2v_watermark=video_i2v_watermark,
                videoedit_model=videoedit_model,
                videoedit_resolution=videoedit_resolution,
                videoedit_duration=videoedit_duration,
                videoedit_prompt_extend=videoedit_prompt_extend,
                videoedit_watermark=videoedit_watermark,
                videoedit_audio_setting=videoedit_audio_setting,
            ),
        },
    }


def load_workspace_config(workspace_root: Path) -> tuple[dict[str, Any], str | None]:
    config_path = workspace_root / CONFIG_FILENAME
    if not config_path.is_file():
        return {}, None

    data = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise InvalidWorkspaceConfigError(
            f"{CONFIG_FILENAME} must contain a JSON object."
        )

    defaults = data.get("defaults")
    if defaults is not None and not isinstance(defaults, dict):
        raise InvalidWorkspaceConfigError("'defaults' must be an object.")

    for mode_name in ("t2i", "i2i"):
        mode_defaults = (defaults or {}).get(mode_name)
        if mode_defaults is not None and not isinstance(mode_defaults, dict):
            raise InvalidWorkspaceConfigError(
                f"'defaults.{mode_name}' must be an object."
            )

    video_defaults = (defaults or {}).get("video")
    if video_defaults is not None and not isinstance(video_defaults, dict):
        raise InvalidWorkspaceConfigError("'defaults.video' must be an object.")
    for mode_name in ("t2v", "i2v", "videoedit"):
        mode_defaults = (video_defaults or {}).get(mode_name)
        if mode_defaults is not None and not isinstance(mode_defaults, dict):
            raise InvalidWorkspaceConfigError(
                f"'defaults.video.{mode_name}' must be an object."
            )

    model = data.get("model")
    if model is not None and not isinstance(model, str):
        raise InvalidWorkspaceConfigError("'model' must be a string.")

    base_url = data.get("base_url")
    if base_url is not None and not isinstance(base_url, str):
        raise InvalidWorkspaceConfigError("'base_url' must be a string.")

    return data, str(config_path)


def resolve_default_model(config: dict[str, Any]) -> str | None:
    value = config.get("model")
    if value is None:
        return None
    return str(value).strip() or None


def resolve_default_base_url(config: dict[str, Any]) -> str:
    value = config.get("base_url")
    if value is None:
        return DEFAULT_BASE_URL
    text = str(value).strip()
    return text or DEFAULT_BASE_URL


def resolve_mode_defaults(
    config: dict[str, Any],
    *,
    has_images: bool,
) -> dict[str, Any]:
    defaults = config.get("defaults")
    if not isinstance(defaults, dict):
        return {}

    mode_name = "i2i" if has_images else "t2i"
    mode_defaults = defaults.get(mode_name)
    if not isinstance(mode_defaults, dict):
        return {}

    return dict(mode_defaults)


def resolve_video_mode_defaults(
    config: dict[str, Any],
    *,
    mode_name: str,
) -> dict[str, Any]:
    defaults = config.get("defaults")
    if not isinstance(defaults, dict):
        return {}

    video_defaults = defaults.get("video")
    if not isinstance(video_defaults, dict):
        return {}

    mode_defaults = video_defaults.get(mode_name)
    if not isinstance(mode_defaults, dict):
        return {}

    return dict(mode_defaults)


def write_workspace_files(
    workspace_root: Path,
    *,
    config: dict[str, Any],
    api_key: str | None = None,
    force: bool = False,
) -> dict[str, str | None]:
    workspace_root.mkdir(parents=True, exist_ok=True)

    config_path = workspace_root / CONFIG_FILENAME
    api_key_path = workspace_root / API_KEY_FILENAME

    if config_path.exists() and not force:
        raise WorkspaceConfigWriteError(
            f"{CONFIG_FILENAME} already exists. Use force to overwrite it."
        )
    if api_key is not None and api_key_path.exists() and not force:
        raise WorkspaceConfigWriteError(
            f"{API_KEY_FILENAME} already exists. Use force to overwrite it."
        )

    config_path.write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    api_key_written: str | None = None
    if api_key is not None:
        value = api_key.strip()
        if not value:
            raise WorkspaceConfigWriteError("API key must not be empty.")
        api_key_path.write_text(value + "\n", encoding="utf-8")
        api_key_written = str(api_key_path)

    return {
        "config_file": str(config_path),
        "api_key_file": api_key_written,
    }
