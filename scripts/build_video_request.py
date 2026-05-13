from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from workspace_config import resolve_video_mode_defaults


VIDEO_GENERATION_ENDPOINT = "/services/aigc/video-generation/video-synthesis"
IMAGE2VIDEO_ENDPOINT = "/services/aigc/image2video/video-synthesis"

SUPPORTED_ENDPOINTS = {
    "video-generation": VIDEO_GENERATION_ENDPOINT,
    "image2video": IMAGE2VIDEO_ENDPOINT,
}

SUPPORTED_PARAMETER_KEYS = {
    "resolution",
    "size",
    "ratio",
    "duration",
    "prompt_extend",
    "watermark",
    "seed",
    "shot_type",
    "audio",
    "audio_setting",
    "obj_or_bg",
    "control_condition",
    "mask_type",
    "expand_ratio",
    "top_scale",
    "bottom_scale",
    "left_scale",
    "right_scale",
}

SUPPORTED_INPUT_KEYS = {
    "prompt",
    "negative_prompt",
    "audio_url",
    "media",
    "img_url",
    "first_frame_url",
    "last_frame_url",
    "reference_urls",
    "reference_video_urls",
    "function",
    "ref_images_url",
    "video_url",
    "mask_image_url",
    "mask_video_url",
    "mask_frame_id",
    "first_clip_url",
    "last_clip_url",
}

MANAGED_VIDEO_MODES = {"t2v", "i2v", "videoedit"}
RAW_VIDEO_MODE = "raw"
RAW_MODE_INPUT_HINTS = {
    "img_url",
    "first_frame_url",
    "last_frame_url",
    "reference_urls",
    "reference_video_urls",
    "function",
    "ref_images_url",
    "video_url",
    "mask_image_url",
    "mask_video_url",
    "mask_frame_id",
    "first_clip_url",
    "last_clip_url",
}


class InvalidVideoSpecError(ValueError):
    """Raised when a video generation spec cannot be sent safely."""


@dataclass(slots=True)
class VideoJobSpec:
    model: str
    input: dict[str, Any]
    parameters: dict[str, Any] = field(default_factory=dict)
    endpoint: str = VIDEO_GENERATION_ENDPOINT
    source_dir: Path = field(default_factory=Path.cwd)


def parse_bool(value: Any, *, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    raise InvalidVideoSpecError(f"Invalid boolean for {field_name}: {value!r}")


def _is_public_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _normalize_public_url(value: Any, *, field_name: str) -> str:
    text = str(value).strip()
    if not _is_public_url(text):
        raise InvalidVideoSpecError(
            f"{field_name} must be a public HTTP/HTTPS URL for video APIs."
        )
    return text


def _coerce_int(value: Any, *, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise InvalidVideoSpecError(f"Invalid integer for {field_name}: {value!r}") from exc


def _normalize_wan27_i2v_media(normalized: list[dict[str, str]]) -> None:
    seen_types: set[str] = set()
    for index, item in enumerate(normalized, start=1):
        media_type = item["type"]
        if media_type not in {"first_frame", "last_frame", "driving_audio", "first_clip"}:
            raise InvalidVideoSpecError(f"media item {index} has unsupported type: {media_type!r}")
        if media_type in seen_types:
            raise InvalidVideoSpecError(f"media type appears more than once: {media_type!r}")
        seen_types.add(media_type)

    media_types = {item["type"] for item in normalized}
    allowed_combinations = [
        {"first_frame"},
        {"first_frame", "driving_audio"},
        {"first_frame", "last_frame"},
        {"first_frame", "last_frame", "driving_audio"},
        {"first_clip"},
        {"first_clip", "last_frame"},
    ]
    if media_types not in allowed_combinations:
        raise InvalidVideoSpecError(
            "media must match a supported wan2.7-i2v combination."
        )


def _normalize_wan27_videoedit_media(normalized: list[dict[str, str]]) -> None:
    video_count = sum(1 for item in normalized if item["type"] == "video")
    reference_count = sum(
        1 for item in normalized if item["type"] in {"reference_image", "first_frame"}
    )
    unsupported = sorted(
        {item["type"] for item in normalized}
        - {"video", "reference_image", "first_frame"}
    )
    if unsupported:
        raise InvalidVideoSpecError(
            f"Unsupported wan2.7-videoedit media types: {', '.join(unsupported)}"
        )
    if video_count != 1:
        raise InvalidVideoSpecError("wan2.7-videoedit media requires exactly one video.")
    if reference_count > 3:
        raise InvalidVideoSpecError(
            "wan2.7-videoedit media supports at most three reference images."
        )


def _normalize_media(items: Any, *, model: str) -> list[dict[str, str]]:
    if not isinstance(items, list) or not items:
        raise InvalidVideoSpecError("media must be a non-empty array.")

    normalized: list[dict[str, str]] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise InvalidVideoSpecError(f"media item {index} must be an object.")
        media_type = str(item.get("type", "")).strip()
        if not media_type:
            raise InvalidVideoSpecError(f"media item {index} must include a type.")
        normalized.append(
            {
                "type": media_type,
                "url": _normalize_public_url(item.get("url"), field_name=f"media[{index}].url"),
            }
        )

    if model == "wan2.7-i2v":
        _normalize_wan27_i2v_media(normalized)
    elif model == "wan2.7-videoedit":
        _normalize_wan27_videoedit_media(normalized)
    return normalized


def _normalize_url_array(value: Any, *, field_name: str, min_items: int = 1) -> list[str]:
    if not isinstance(value, list) or len(value) < min_items:
        raise InvalidVideoSpecError(f"{field_name} must be a non-empty array.")
    return [
        _normalize_public_url(item, field_name=f"{field_name}[{index}]")
        for index, item in enumerate(value)
    ]


def _normalize_input(
    raw_input: dict[str, Any],
    *,
    model: str,
    strict: bool,
) -> dict[str, Any]:
    unsupported = sorted(set(raw_input) - SUPPORTED_INPUT_KEYS)
    if strict and unsupported:
        raise InvalidVideoSpecError(f"Unsupported video input keys: {', '.join(unsupported)}")

    normalized: dict[str, Any] = {}
    for key, value in raw_input.items():
        if value is None:
            continue
        if key in {"prompt", "negative_prompt", "function"}:
            text = str(value).strip()
            if text:
                normalized[key] = text
            continue
        if key == "media":
            normalized[key] = _normalize_media(value, model=model)
            continue
        if key in {
            "audio_url",
            "img_url",
            "first_frame_url",
            "last_frame_url",
            "video_url",
            "mask_image_url",
            "mask_video_url",
            "first_clip_url",
            "last_clip_url",
        }:
            normalized[key] = _normalize_public_url(value, field_name=key)
            continue
        if key in {"reference_urls", "reference_video_urls", "ref_images_url"}:
            normalized[key] = _normalize_url_array(value, field_name=key)
            continue
        if key == "mask_frame_id":
            normalized[key] = _coerce_int(value, field_name=key)
            continue
        normalized[key] = value

    if strict and model != "wan2.7-i2v" and not normalized.get("prompt"):
        raise InvalidVideoSpecError("input.prompt is required.")
    return normalized


def _normalize_parameters(
    raw_parameters: dict[str, Any],
    *,
    strict: bool,
) -> dict[str, Any]:
    unsupported = sorted(set(raw_parameters) - SUPPORTED_PARAMETER_KEYS)
    if strict and unsupported:
        raise InvalidVideoSpecError(
            f"Unsupported video parameter keys: {', '.join(unsupported)}"
        )

    normalized: dict[str, Any] = {}
    for key, value in raw_parameters.items():
        if value is None:
            continue
        if key in {"prompt_extend", "watermark", "audio"}:
            normalized[key] = parse_bool(value, field_name=key)
            continue
        if key in {"duration", "seed"}:
            normalized[key] = _coerce_int(value, field_name=key)
            continue
        normalized[key] = value

    if "seed" in normalized and not 0 <= normalized["seed"] <= 2_147_483_647:
        raise InvalidVideoSpecError("seed must be within [0, 2147483647].")
    if "duration" in normalized and normalized["duration"] < 0:
        raise InvalidVideoSpecError("duration must be non-negative.")
    return normalized


def _endpoint_from_name(value: Any) -> str:
    if value is None:
        return VIDEO_GENERATION_ENDPOINT
    text = str(value).strip()
    if text in SUPPORTED_ENDPOINTS:
        return SUPPORTED_ENDPOINTS[text]
    if text.startswith("/"):
        if text not in set(SUPPORTED_ENDPOINTS.values()):
            raise InvalidVideoSpecError(f"Unsupported video endpoint: {text!r}")
        return text
    raise InvalidVideoSpecError(
        f"Unsupported video endpoint: {text!r}. Use video-generation or image2video."
    )


def _media_types(raw_input: dict[str, Any]) -> set[str]:
    media = raw_input.get("media")
    if not isinstance(media, list):
        return set()
    media_types: set[str] = set()
    for item in media:
        if isinstance(item, dict):
            media_type = str(item.get("type", "")).strip()
            if media_type:
                media_types.add(media_type)
    return media_types


def _infer_video_mode_name(model_hint: str | None, raw_input: dict[str, Any]) -> str:
    if model_hint is not None:
        if model_hint == "wan2.7-videoedit":
            return "videoedit"
        if model_hint == "wan2.7-i2v":
            return "i2v"
        if "-t2v" in model_hint:
            return "t2v"
        return RAW_VIDEO_MODE

    if any(key in raw_input for key in RAW_MODE_INPUT_HINTS):
        return RAW_VIDEO_MODE

    media_types = _media_types(raw_input)
    if "video" in media_types or "reference_image" in media_types:
        return "videoedit"
    if media_types:
        return "i2v"
    return "t2v"


def _default_model_for_mode(mode_name: str) -> str | None:
    if mode_name == "videoedit":
        return "wan2.7-videoedit"
    if mode_name == "i2v":
        return "wan2.7-i2v"
    if mode_name == "t2v":
        return "wan2.6-t2v"
    return None


def load_video_job_spec(
    *,
    spec_file: Path | None,
    prompt: str | None,
    media: list[str] | None,
    input_overrides: dict[str, Any] | None,
    parameters: dict[str, Any] | None,
    model: str | None,
    endpoint: str | None,
    workspace_root: Path,
    workspace_config: dict[str, Any] | None = None,
) -> VideoJobSpec:
    base_data: dict[str, Any] = {}
    source_dir = workspace_root
    config = workspace_config or {}
    if spec_file is not None:
        source_dir = spec_file.resolve().parent
        base_data = json.loads(spec_file.read_text(encoding="utf-8"))
        if not isinstance(base_data, dict):
            raise InvalidVideoSpecError("spec-file must contain a JSON object.")

    raw_input = base_data.get("input", {})
    if not isinstance(raw_input, dict):
        raise InvalidVideoSpecError("input in spec-file must be an object.")
    merged_input = dict(raw_input)
    if prompt is not None:
        merged_input["prompt"] = prompt
    if media:
        merged_input["media"] = []
        for item in media:
            if "=" not in item:
                raise InvalidVideoSpecError(
                    "media entries must use TYPE=URL, e.g. first_frame=https://..."
                )
            media_type, media_url = item.split("=", 1)
            merged_input["media"].append({"type": media_type.strip(), "url": media_url.strip()})
    if input_overrides:
        merged_input.update(input_overrides)

    model_hint = str(model or base_data.get("model") or "").strip() or None
    video_mode_name = _infer_video_mode_name(model_hint, merged_input)
    if video_mode_name in MANAGED_VIDEO_MODES:
        config_defaults = resolve_video_mode_defaults(config, mode_name=video_mode_name)
    else:
        config_defaults = {}
    config_model = config_defaults.pop("model", None)

    raw_parameters = base_data.get("parameters", {})
    if not isinstance(raw_parameters, dict):
        raise InvalidVideoSpecError("parameters in spec-file must be an object.")
    merged_parameters = dict(config_defaults)
    merged_parameters.update(raw_parameters)
    if parameters:
        merged_parameters.update(parameters)

    default_model = _default_model_for_mode(video_mode_name)
    model_value = model or base_data.get("model") or config_model or default_model
    merged_model = str(model_value).strip() if model_value is not None else ""
    if not merged_model:
        raise InvalidVideoSpecError("model is required for advanced video specs.")
    if merged_model == "wan2.7-i2v" and not merged_input.get("media"):
        raise InvalidVideoSpecError("wan2.7-i2v requires input.media.")
    if merged_model == "wan2.7-videoedit" and not merged_input.get("media"):
        raise InvalidVideoSpecError("wan2.7-videoedit requires input.media.")

    strict_validation = video_mode_name in MANAGED_VIDEO_MODES
    merged_endpoint = _endpoint_from_name(endpoint or base_data.get("endpoint"))
    return VideoJobSpec(
        model=merged_model,
        input=_normalize_input(
            merged_input,
            model=merged_model,
            strict=strict_validation,
        ),
        parameters=_normalize_parameters(merged_parameters, strict=strict_validation),
        endpoint=merged_endpoint,
        source_dir=source_dir,
    )


def build_video_request_payload(job: VideoJobSpec) -> dict[str, Any]:
    payload = {
        "model": job.model,
        "input": job.input,
    }
    if job.parameters:
        payload["parameters"] = job.parameters
    return payload
