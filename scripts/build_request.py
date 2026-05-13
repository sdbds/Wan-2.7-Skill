from __future__ import annotations

import base64
import json
import mimetypes
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from workspace_config import resolve_default_model, resolve_mode_defaults


MAX_IMAGE_BYTES = 20 * 1024 * 1024
SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
PIXEL_SIZE_PATTERN = re.compile(r"^\d{3,5}\*\d{3,5}$")
HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")
RATIO_PATTERN = re.compile(r"^\d{1,3}\.\d{2}%$")
SUPPORTED_MODELS = {"wan2.7-image", "wan2.7-image-pro"}
SUPPORTED_PARAMETER_KEYS = {
    "size",
    "n",
    "seed",
    "watermark",
    "enable_sequential",
    "thinking_mode",
    "color_palette",
    "bbox_list",
}


class InvalidJobSpecError(ValueError):
    """Raised when the input spec is incomplete or incompatible."""


@dataclass(slots=True)
class JobSpec:
    prompt: str
    images: list[str] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)
    model: str = "wan2.7-image"
    source_dir: Path = field(default_factory=Path.cwd)

    @property
    def mode(self) -> str:
        return "i2i" if self.images else "t2i"


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
    raise InvalidJobSpecError(f"Invalid boolean for {field_name}: {value!r}")


def _is_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"}


def _normalize_model(value: Any) -> str:
    model = str(value).strip()
    if model not in SUPPORTED_MODELS:
        raise InvalidJobSpecError(
            f"Unsupported model: {model!r}. Supported: {', '.join(sorted(SUPPORTED_MODELS))}"
        )
    return model


def _coerce_image_reference(value: str, source_dir: Path) -> str:
    if _is_url(value):
        return value

    image_path = Path(value)
    if not image_path.is_absolute():
        image_path = (source_dir / image_path).resolve()
    else:
        image_path = image_path.resolve()

    if not image_path.is_file():
        raise InvalidJobSpecError(f"Image file does not exist: {image_path}")

    if image_path.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise InvalidJobSpecError(
            f"Unsupported image format for {image_path}. "
            f"Supported: {', '.join(sorted(SUPPORTED_SUFFIXES))}"
        )

    file_bytes = image_path.read_bytes()
    if len(file_bytes) > MAX_IMAGE_BYTES:
        raise InvalidJobSpecError(
            f"Image file is larger than 20MB and cannot be sent: {image_path}"
        )

    mime_type, _ = mimetypes.guess_type(str(image_path))
    if not mime_type:
        mime_type = "application/octet-stream"

    encoded = base64.b64encode(file_bytes).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _coerce_int(value: Any, *, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise InvalidJobSpecError(f"Invalid integer for {field_name}: {value!r}") from exc


def _normalize_size(
    value: Any,
    *,
    model: str,
    has_images: bool,
    enable_sequential: bool,
) -> str:
    if value is None:
        return "2K" if model == "wan2.7-image-pro" else "1K"

    normalized = str(value).strip().upper()

    preset_sizes = {"1K", "2K"}
    if model == "wan2.7-image-pro":
        preset_sizes.add("4K")
    elif normalized == "4K":
        raise InvalidJobSpecError("wan2.7-image does not support 4K output.")

    if normalized in preset_sizes:
        if normalized == "4K" and (has_images or enable_sequential):
            raise InvalidJobSpecError(
                "4K is only valid for wan2.7-image-pro text-to-image without sequential generation."
            )
        return normalized

    if PIXEL_SIZE_PATTERN.fullmatch(normalized):
        width_text, height_text = normalized.split("*", 1)
        width = int(width_text)
        height = int(height_text)
        total_pixels = width * height
        if total_pixels < 768 * 768:
            raise InvalidJobSpecError("size total pixels must be at least 768*768.")

        max_pixels = 2048 * 2048
        if model == "wan2.7-image-pro" and not has_images and not enable_sequential:
            max_pixels = 4096 * 4096
        if total_pixels > max_pixels:
            raise InvalidJobSpecError(
                f"size total pixels exceed model/scenario limit ({max_pixels})."
            )

        ratio = max(width / height, height / width)
        if ratio > 8:
            raise InvalidJobSpecError("size aspect ratio must stay within [1:8, 8:1].")
        return normalized

    raise InvalidJobSpecError(
        "size must be a supported preset (1K/2K/4K) or a pixel string like 1536*1024."
    )


def _normalize_color_palette(
    value: Any, *, enable_sequential: bool
) -> list[dict[str, str]]:
    if enable_sequential:
        raise InvalidJobSpecError(
            "color_palette is only valid when enable_sequential is false."
        )
    if not isinstance(value, list):
        raise InvalidJobSpecError("color_palette must be an array.")
    if not 3 <= len(value) <= 10:
        raise InvalidJobSpecError("color_palette must contain between 3 and 10 colors.")

    normalized_items: list[dict[str, str]] = []
    ratio_total = Decimal("0.00")
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise InvalidJobSpecError(
                f"color_palette item {index} must be an object with hex and ratio."
            )
        hex_value = str(item.get("hex", "")).strip()
        ratio_value = str(item.get("ratio", "")).strip()
        if not HEX_COLOR_PATTERN.fullmatch(hex_value):
            raise InvalidJobSpecError(
                f"color_palette item {index} has invalid hex: {hex_value!r}"
            )
        if not RATIO_PATTERN.fullmatch(ratio_value):
            raise InvalidJobSpecError(
                f"color_palette item {index} has invalid ratio: {ratio_value!r}"
            )
        try:
            ratio_total += Decimal(ratio_value[:-1])
        except InvalidOperation as exc:
            raise InvalidJobSpecError(
                f"color_palette item {index} has invalid ratio: {ratio_value!r}"
            ) from exc
        normalized_items.append({"hex": hex_value.upper(), "ratio": ratio_value})

    if ratio_total != Decimal("100.00"):
        raise InvalidJobSpecError("color_palette ratio total must equal 100.00%.")

    return normalized_items


def _normalize_bbox_list(
    value: Any,
    *,
    has_images: bool,
    image_count: int,
) -> list[list[list[int]]]:
    if not has_images:
        raise InvalidJobSpecError(
            "bbox_list is only valid when input images are provided."
        )
    if not isinstance(value, list):
        raise InvalidJobSpecError("bbox_list must be an array.")
    if len(value) != image_count:
        raise InvalidJobSpecError(
            "bbox_list length must equal the number of input images."
        )

    normalized_images: list[list[list[int]]] = []
    for image_index, image_boxes in enumerate(value, start=1):
        if not isinstance(image_boxes, list):
            raise InvalidJobSpecError(
                f"bbox_list item {image_index} must be an array of boxes."
            )
        if len(image_boxes) > 2:
            raise InvalidJobSpecError(
                f"bbox_list item {image_index} supports at most 2 boxes."
            )

        normalized_boxes: list[list[int]] = []
        for box_index, box in enumerate(image_boxes, start=1):
            if not isinstance(box, list) or len(box) != 4:
                raise InvalidJobSpecError(
                    f"bbox_list item {image_index} box {box_index} must be [x1, y1, x2, y2]."
                )
            if any(not isinstance(coord, int) or isinstance(coord, bool) for coord in box):
                raise InvalidJobSpecError(
                    f"bbox_list item {image_index} box {box_index} must contain integers only."
                )

            x1, y1, x2, y2 = box
            if min(x1, y1, x2, y2) < 0:
                raise InvalidJobSpecError(
                    f"bbox_list item {image_index} box {box_index} must use non-negative coordinates."
                )
            if not x1 < x2 or not y1 < y2:
                raise InvalidJobSpecError(
                    f"bbox_list item {image_index} box {box_index} must satisfy x1 < x2 and y1 < y2."
                )
            normalized_boxes.append([x1, y1, x2, y2])

        normalized_images.append(normalized_boxes)

    return normalized_images


def _normalize_parameters(
    raw_parameters: dict[str, Any],
    *,
    has_images: bool,
    image_count: int,
    model: str,
) -> tuple[dict[str, Any], list[str]]:
    unsupported_keys = sorted(set(raw_parameters) - SUPPORTED_PARAMETER_KEYS)
    if unsupported_keys:
        raise InvalidJobSpecError(
            f"Unsupported parameters for V1 demo: {', '.join(unsupported_keys)}"
        )

    enable_sequential = False
    if raw_parameters.get("enable_sequential") is not None:
        enable_sequential = parse_bool(
            raw_parameters["enable_sequential"], field_name="enable_sequential"
        )

    default_n = 12 if enable_sequential else 4
    parameters: dict[str, Any] = {
        "size": _normalize_size(
            raw_parameters.get("size"),
            model=model,
            has_images=has_images,
            enable_sequential=enable_sequential,
        ),
        "n": default_n
        if raw_parameters.get("n") is None
        else _coerce_int(raw_parameters["n"], field_name="n"),
        "watermark": False
        if raw_parameters.get("watermark") is None
        else parse_bool(raw_parameters["watermark"], field_name="watermark"),
        "enable_sequential": enable_sequential,
    }

    if not 1 <= parameters["n"] <= (12 if parameters["enable_sequential"] else 4):
        raise InvalidJobSpecError(
            f"n={parameters['n']} is out of range for "
            f"{'sequential' if parameters['enable_sequential'] else 'normal'} mode."
        )

    if raw_parameters.get("seed") is not None:
        seed = _coerce_int(raw_parameters["seed"], field_name="seed")
        if not 0 <= seed <= 2_147_483_647:
            raise InvalidJobSpecError("seed must be within [0, 2147483647].")
        parameters["seed"] = seed

    thinking_mode = raw_parameters.get("thinking_mode")
    if thinking_mode is not None:
        if has_images or parameters["enable_sequential"]:
            raise InvalidJobSpecError(
                "thinking_mode is only valid for text-to-image without sequential generation."
            )
        parameters["thinking_mode"] = parse_bool(
            thinking_mode, field_name="thinking_mode"
        )

    color_palette = raw_parameters.get("color_palette")
    if color_palette is not None:
        parameters["color_palette"] = _normalize_color_palette(
            color_palette, enable_sequential=parameters["enable_sequential"]
        )

    bbox_list = raw_parameters.get("bbox_list")
    if bbox_list is not None:
        parameters["bbox_list"] = _normalize_bbox_list(
            bbox_list,
            has_images=has_images,
            image_count=image_count,
        )

    return parameters, []


def load_job_spec(
    *,
    spec_file: Path | None,
    prompt: str | None,
    images: list[str] | None,
    parameters: dict[str, Any] | None,
    model: str | None,
    workspace_root: Path,
    workspace_config: dict[str, Any] | None = None,
) -> JobSpec:
    base_data: dict[str, Any] = {}
    source_dir = workspace_root
    config = workspace_config or {}

    if spec_file is not None:
        source_dir = spec_file.resolve().parent
        base_data = json.loads(spec_file.read_text(encoding="utf-8"))
        if not isinstance(base_data, dict):
            raise InvalidJobSpecError("spec-file must contain a JSON object.")

    merged_prompt = prompt if prompt is not None else base_data.get("prompt", "")
    raw_images = base_data.get("images", [])
    if raw_images is None:
        raw_images = []
    if not isinstance(raw_images, list):
        raise InvalidJobSpecError("images in spec-file must be an array.")
    merged_images = list(raw_images)
    if images:
        merged_images = list(images)

    base_parameters = base_data.get("parameters", {})
    if not isinstance(base_parameters, dict):
        raise InvalidJobSpecError("parameters in spec-file must be an object.")
    merged_parameters = resolve_mode_defaults(config, has_images=bool(merged_images))
    merged_parameters.update(base_parameters)
    if parameters:
        merged_parameters.update(parameters)

    merged_model = _normalize_model(
        model or base_data.get("model") or resolve_default_model(config) or "wan2.7-image"
    )
    merged_prompt = str(merged_prompt).strip()
    if not merged_prompt:
        raise InvalidJobSpecError("prompt is required.")

    if len(merged_images) > 9:
        raise InvalidJobSpecError("wan2.7-image accepts at most 9 input images.")

    return JobSpec(
        prompt=merged_prompt,
        images=[str(item) for item in merged_images],
        parameters=merged_parameters,
        model=str(merged_model),
        source_dir=source_dir,
    )


def build_request_payload(job: JobSpec) -> tuple[dict[str, Any], list[str]]:
    if job.images:
        image_values = [_coerce_image_reference(item, job.source_dir) for item in job.images]
    else:
        image_values = []

    parameters, warnings = _normalize_parameters(
        job.parameters,
        has_images=bool(image_values),
        image_count=len(image_values),
        model=job.model,
    )

    content: list[dict[str, Any]] = [{"text": job.prompt}]
    for image_value in image_values:
        content.append({"image": image_value})

    payload = {
        "model": job.model,
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": content,
                }
            ]
        },
        "parameters": parameters,
    }
    return payload, warnings
