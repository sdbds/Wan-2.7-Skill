from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from build_video_request import (
    IMAGE2VIDEO_ENDPOINT,
    VIDEO_GENERATION_ENDPOINT,
    InvalidVideoSpecError,
    build_video_request_payload,
    load_video_job_spec,
)
from normalize_video_response import normalize_video_result


def test_wan27_i2v_media_payload_from_cli_args(tmp_path: Path):
    job = load_video_job_spec(
        spec_file=None,
        prompt="Make the character walk forward.",
        media=["first_frame=https://example.com/frame.png"],
        input_overrides=None,
        parameters={"resolution": "720P", "duration": "5", "prompt_extend": "false"},
        model=None,
        endpoint=None,
        workspace_root=tmp_path,
    )

    payload = build_video_request_payload(job)

    assert job.endpoint == VIDEO_GENERATION_ENDPOINT
    assert payload["model"] == "wan2.7-i2v"
    assert payload["input"]["media"] == [
        {"type": "first_frame", "url": "https://example.com/frame.png"}
    ]
    assert payload["parameters"]["resolution"] == "720P"
    assert payload["parameters"]["duration"] == 5
    assert payload["parameters"]["prompt_extend"] is False


def test_wan27_i2v_allows_promptless_media_payload(tmp_path: Path):
    job = load_video_job_spec(
        spec_file=None,
        prompt=None,
        media=["first_frame=https://example.com/frame.png"],
        input_overrides=None,
        parameters={"resolution": "720P"},
        model=None,
        endpoint=None,
        workspace_root=tmp_path,
    )

    payload = build_video_request_payload(job)

    assert payload["model"] == "wan2.7-i2v"
    assert "prompt" not in payload["input"]


def test_t2v_defaults_when_no_media(tmp_path: Path):
    job = load_video_job_spec(
        spec_file=None,
        prompt="A slow cinematic product shot.",
        media=None,
        input_overrides=None,
        parameters={"size": "1280*720"},
        model=None,
        endpoint=None,
        workspace_root=tmp_path,
    )

    payload = build_video_request_payload(job)

    assert payload["model"] == "wan2.6-t2v"
    assert payload["input"]["prompt"] == "A slow cinematic product shot."
    assert payload["parameters"]["size"] == "1280*720"


def test_t2v_uses_workspace_video_defaults(tmp_path: Path):
    job = load_video_job_spec(
        spec_file=None,
        prompt="A slow cinematic product shot.",
        media=None,
        input_overrides=None,
        parameters=None,
        model=None,
        endpoint=None,
        workspace_root=tmp_path,
        workspace_config={
            "defaults": {
                "video": {
                    "t2v": {
                        "model": "wan2.6-t2v",
                        "size": "1280*720",
                        "duration": 2,
                        "prompt_extend": True,
                        "watermark": False,
                    }
                }
            }
        },
    )

    payload = build_video_request_payload(job)

    assert payload["model"] == "wan2.6-t2v"
    assert payload["parameters"] == {
        "size": "1280*720",
        "duration": 2,
        "prompt_extend": True,
        "watermark": False,
    }


def test_explicit_video_parameters_override_workspace_defaults(tmp_path: Path):
    job = load_video_job_spec(
        spec_file=None,
        prompt="A slow cinematic product shot.",
        media=None,
        input_overrides=None,
        parameters={"duration": 5},
        model=None,
        endpoint=None,
        workspace_root=tmp_path,
        workspace_config={
            "defaults": {
                "video": {
                    "t2v": {
                        "duration": 2,
                        "size": "1280*720",
                    }
                }
            }
        },
    )

    payload = build_video_request_payload(job)

    assert payload["parameters"]["duration"] == 5
    assert payload["parameters"]["size"] == "1280*720"


def test_spec_file_supports_reference_video_endpoint_selection(tmp_path: Path):
    spec_path = tmp_path / "job.json"
    spec_path.write_text(
        json.dumps(
            {
                "model": "wan2.6-r2v-flash",
                "endpoint": "video-generation",
                "input": {
                    "prompt": "character1 waves to the camera.",
                    "reference_urls": ["https://example.com/ref.mp4"],
                },
                "parameters": {
                    "size": "1280*720",
                    "duration": 5,
                    "audio": False,
                },
            }
        ),
        encoding="utf-8",
    )

    job = load_video_job_spec(
        spec_file=spec_path,
        prompt=None,
        media=None,
        input_overrides=None,
        parameters=None,
        model=None,
        endpoint=None,
        workspace_root=tmp_path,
    )

    assert job.model == "wan2.6-r2v-flash"
    assert job.endpoint == VIDEO_GENERATION_ENDPOINT
    assert job.input["reference_urls"] == ["https://example.com/ref.mp4"]
    assert job.parameters["audio"] is False


def test_advanced_r2v_spec_does_not_receive_t2v_defaults(tmp_path: Path):
    spec_path = tmp_path / "job.json"
    spec_path.write_text(
        json.dumps(
            {
                "model": "wan2.6-r2v-flash",
                "endpoint": "video-generation",
                "input": {
                    "prompt": "character1 waves to the camera.",
                    "reference_urls": ["https://example.com/ref.mp4"],
                },
                "parameters": {
                    "audio": False,
                },
            }
        ),
        encoding="utf-8",
    )

    job = load_video_job_spec(
        spec_file=spec_path,
        prompt=None,
        media=None,
        input_overrides=None,
        parameters=None,
        model=None,
        endpoint=None,
        workspace_root=tmp_path,
        workspace_config={
            "defaults": {
                "video": {
                    "t2v": {
                        "model": "wan2.6-t2v",
                        "size": "1280*720",
                        "duration": 2,
                        "prompt_extend": True,
                    }
                }
            }
        },
    )

    assert job.parameters == {"audio": False}


def test_raw_vace_spec_preserves_unknown_fields(tmp_path: Path):
    spec_path = tmp_path / "job.json"
    spec_path.write_text(
        json.dumps(
            {
                "model": "wan2.1-vace-plus",
                "input": {
                    "function": "video_extension",
                    "prompt": "Extend this video naturally.",
                    "video_url": "https://example.com/input.mp4",
                    "future_input_field": {"keep": True},
                },
                "parameters": {
                    "duration": "5",
                    "future_parameter": "official-api-owned",
                },
            }
        ),
        encoding="utf-8",
    )

    job = load_video_job_spec(
        spec_file=spec_path,
        prompt=None,
        media=None,
        input_overrides=None,
        parameters=None,
        model=None,
        endpoint=None,
        workspace_root=tmp_path,
    )

    assert job.input["future_input_field"] == {"keep": True}
    assert job.parameters["duration"] == 5
    assert job.parameters["future_parameter"] == "official-api-owned"


def test_advanced_spec_without_model_is_rejected(tmp_path: Path):
    with pytest.raises(InvalidVideoSpecError, match="model is required"):
        load_video_job_spec(
            spec_file=None,
            prompt="character1 waves.",
            media=None,
            input_overrides={"reference_urls": ["https://example.com/ref.mp4"]},
            parameters=None,
            model=None,
            endpoint=None,
            workspace_root=tmp_path,
        )


def test_managed_t2v_still_rejects_unknown_parameters(tmp_path: Path):
    with pytest.raises(InvalidVideoSpecError, match="Unsupported video parameter keys"):
        load_video_job_spec(
            spec_file=None,
            prompt="A slow cinematic product shot.",
            media=None,
            input_overrides=None,
            parameters={"future_parameter": "not-for-managed-mode"},
            model=None,
            endpoint=None,
            workspace_root=tmp_path,
        )


def test_image2video_endpoint_alias(tmp_path: Path):
    job = load_video_job_spec(
        spec_file=None,
        prompt="Transition from first frame to last frame.",
        media=None,
        input_overrides={
            "first_frame_url": "https://example.com/first.png",
            "last_frame_url": "https://example.com/last.png",
        },
        parameters={"resolution": "720P"},
        model="wan2.2-kf2v-flash",
        endpoint="image2video",
        workspace_root=tmp_path,
    )

    assert job.endpoint == IMAGE2VIDEO_ENDPOINT
    assert job.input["first_frame_url"] == "https://example.com/first.png"


def test_wan27_videoedit_media_allows_video_and_reference_images(tmp_path: Path):
    job = load_video_job_spec(
        spec_file=None,
        prompt="Change the style to watercolor while preserving the motion.",
        media=[
            "video=https://example.com/input.mp4",
            "reference_image=https://example.com/style.png",
        ],
        input_overrides=None,
        parameters={"resolution": "720P", "ratio": "16:9", "audio_setting": "origin"},
        model="wan2.7-videoedit",
        endpoint=None,
        workspace_root=tmp_path,
    )

    payload = build_video_request_payload(job)

    assert payload["model"] == "wan2.7-videoedit"
    assert payload["input"]["media"] == [
        {"type": "video", "url": "https://example.com/input.mp4"},
        {"type": "reference_image", "url": "https://example.com/style.png"},
    ]
    assert payload["parameters"]["ratio"] == "16:9"
    assert payload["parameters"]["audio_setting"] == "origin"


def test_videoedit_model_is_inferred_from_video_media(tmp_path: Path):
    job = load_video_job_spec(
        spec_file=None,
        prompt="Change the style to watercolor.",
        media=["video=https://example.com/input.mp4"],
        input_overrides=None,
        parameters=None,
        model=None,
        endpoint=None,
        workspace_root=tmp_path,
    )

    payload = build_video_request_payload(job)

    assert payload["model"] == "wan2.7-videoedit"
    assert payload["input"]["media"] == [
        {"type": "video", "url": "https://example.com/input.mp4"}
    ]


def test_wan27_videoedit_rejects_missing_source_video(tmp_path: Path):
    with pytest.raises(InvalidVideoSpecError, match="exactly one video"):
        load_video_job_spec(
            spec_file=None,
            prompt="Change the style.",
            media=["reference_image=https://example.com/style.png"],
            input_overrides=None,
            parameters=None,
            model="wan2.7-videoedit",
            endpoint=None,
            workspace_root=tmp_path,
        )


def test_rejects_local_media_paths(tmp_path: Path):
    with pytest.raises(InvalidVideoSpecError, match="public HTTP/HTTPS URL"):
        load_video_job_spec(
            spec_file=None,
            prompt="Animate this.",
            media=["first_frame=C:/tmp/frame.png"],
            input_overrides=None,
            parameters=None,
            model=None,
            endpoint=None,
            workspace_root=tmp_path,
        )


def test_normalize_video_response_extracts_video_url():
    normalized = normalize_video_result(
        {
            "request_id": "req",
            "output": {
                "task_id": "task",
                "task_status": "SUCCEEDED",
                "video_url": "https://example.com/out.mp4",
            },
            "usage": {"duration": 5},
        }
    )

    assert normalized["remote_videos"] == ["https://example.com/out.mp4"]
    assert normalized["usage"] == {"duration": 5}
