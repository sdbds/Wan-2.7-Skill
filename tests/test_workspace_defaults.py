from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from build_request import JobSpec, build_request_payload, load_job_spec
from workspace_config import (
    CONFIG_FILENAME,
    InvalidWorkspaceConfigError,
    API_KEY_FILENAME,
    build_workspace_config,
    load_workspace_config,
    resolve_default_base_url,
    write_workspace_files,
)


def _workspace_config() -> dict[str, object]:
    return {
        "model": "wan2.7-image-pro",
        "base_url": "https://dashscope-intl.aliyuncs.com/api/v1",
        "defaults": {
            "t2i": {
                "size": "2K",
                "n": 1,
                "watermark": False,
                "thinking_mode": True,
            },
            "i2i": {
                "size": "1K",
                "n": 1,
                "watermark": False,
            },
        },
    }


def test_t2i_job_uses_workspace_defaults(tmp_path: Path):
    job = load_job_spec(
        spec_file=None,
        prompt="A calm test prompt.",
        images=None,
        parameters=None,
        model=None,
        workspace_root=tmp_path,
        workspace_config=_workspace_config(),
    )

    payload, _ = build_request_payload(job)

    assert job.model == "wan2.7-image-pro"
    assert payload["parameters"]["size"] == "2K"
    assert payload["parameters"]["n"] == 1
    assert payload["parameters"]["watermark"] is False
    assert payload["parameters"]["thinking_mode"] is True


def test_i2i_job_uses_i2i_defaults_and_avoids_t2i_only_fields(tmp_path: Path):
    job = load_job_spec(
        spec_file=None,
        prompt="Edit this naturally.",
        images=["https://example.com/ref.png"],
        parameters=None,
        model=None,
        workspace_root=tmp_path,
        workspace_config=_workspace_config(),
    )

    payload, _ = build_request_payload(job)

    assert payload["parameters"]["size"] == "1K"
    assert payload["parameters"]["n"] == 1
    assert payload["parameters"]["watermark"] is False
    assert "thinking_mode" not in payload["parameters"]


def test_explicit_parameters_override_workspace_defaults(tmp_path: Path):
    job = load_job_spec(
        spec_file=None,
        prompt="A calm test prompt.",
        images=None,
        parameters={"size": "1K", "n": 2, "watermark": "true"},
        model="wan2.7-image",
        workspace_root=tmp_path,
        workspace_config=_workspace_config(),
    )

    payload, _ = build_request_payload(job)

    assert job.model == "wan2.7-image"
    assert payload["parameters"]["size"] == "1K"
    assert payload["parameters"]["n"] == 2
    assert payload["parameters"]["watermark"] is True


def test_load_workspace_config_reads_file_and_base_url(tmp_path: Path):
    config_path = tmp_path / CONFIG_FILENAME
    config_path.write_text(json.dumps(_workspace_config()), encoding="utf-8")

    config, source = load_workspace_config(tmp_path)

    assert source == str(config_path)
    assert resolve_default_base_url(config) == "https://dashscope-intl.aliyuncs.com/api/v1"


def test_invalid_workspace_config_shape_raises(tmp_path: Path):
    config_path = tmp_path / CONFIG_FILENAME
    config_path.write_text(json.dumps({"defaults": []}), encoding="utf-8")

    with pytest.raises(InvalidWorkspaceConfigError, match="'defaults' must be an object"):
        load_workspace_config(tmp_path)


def test_build_workspace_config_requires_concrete_pixel_sizes():
    with pytest.raises(
        InvalidWorkspaceConfigError,
        match="t2i_size must be a concrete pixel size",
    ):
        build_workspace_config(
            model="wan2.7-image",
            base_url="https://dashscope.aliyuncs.com/api/v1",
            t2i_size="1K",
            t2i_n=1,
            t2i_watermark=False,
            t2i_thinking_mode=True,
            i2i_size="1024*1024",
            i2i_n=1,
            i2i_watermark=False,
        )


def test_write_workspace_files_writes_config_and_api_key(tmp_path: Path):
    config = build_workspace_config(
        model="wan2.7-image",
        base_url="https://dashscope.aliyuncs.com/api/v1",
        t2i_size="1024*1024",
        t2i_n=1,
        t2i_watermark=False,
        t2i_thinking_mode=True,
        i2i_size="1024*1024",
        i2i_n=1,
        i2i_watermark=False,
    )

    result = write_workspace_files(tmp_path, config=config, api_key="test-key")

    assert result["config_file"] == str(tmp_path / CONFIG_FILENAME)
    assert result["api_key_file"] == str(tmp_path / API_KEY_FILENAME)
    saved_config = json.loads((tmp_path / CONFIG_FILENAME).read_text(encoding="utf-8"))
    assert saved_config["defaults"]["t2i"]["size"] == "1024*1024"
    assert saved_config["defaults"]["video"]["t2v"]["model"] == "wan2.7-t2v"
    assert saved_config["defaults"]["video"]["t2v"]["size"] == "1280*720"
    assert saved_config["defaults"]["video"]["i2v"]["resolution"] == "720P"
    assert saved_config["defaults"]["video"]["videoedit"]["duration"] == 0
    assert (tmp_path / API_KEY_FILENAME).read_text(encoding="utf-8") == "test-key\n"


def test_build_workspace_config_rejects_invalid_video_resolution():
    with pytest.raises(
        InvalidWorkspaceConfigError,
        match="video_i2v_resolution must be one of",
    ):
        build_workspace_config(
            model="wan2.7-image",
            base_url="https://dashscope.aliyuncs.com/api/v1",
            t2i_size="1024*1024",
            t2i_n=1,
            t2i_watermark=False,
            t2i_thinking_mode=True,
            i2i_size="1024*1024",
            i2i_n=1,
            i2i_watermark=False,
            video_i2v_resolution="4K",
        )


def test_init_workspace_config_script_writes_files(tmp_path: Path):
    script_path = SCRIPT_DIR / "init_workspace_config.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--workspace-root",
            str(tmp_path),
            "--api-key",
            "test-key",
            "--model",
            "wan2.7-image",
            "--t2i-size",
            "1024*1024",
            "--t2i-n",
            "1",
            "--t2i-watermark",
            "false",
            "--t2i-thinking-mode",
            "true",
            "--i2i-size",
            "1344*768",
            "--i2i-n",
            "1",
            "--i2i-watermark",
            "false",
            "--video-t2v-duration",
            "3",
            "--video-i2v-resolution",
            "1080P",
            "--videoedit-audio-setting",
            "auto",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    assert summary["status"] == "success"
    saved_config = json.loads((tmp_path / CONFIG_FILENAME).read_text(encoding="utf-8"))
    assert saved_config["defaults"]["t2i"]["size"] == "1024*1024"
    assert saved_config["defaults"]["i2i"]["size"] == "1344*768"
    assert saved_config["defaults"]["video"]["t2v"]["model"] == "wan2.7-t2v"
    assert saved_config["defaults"]["video"]["t2v"]["duration"] == 3
    assert saved_config["defaults"]["video"]["i2v"]["resolution"] == "1080P"
    assert saved_config["defaults"]["video"]["videoedit"]["audio_setting"] == "auto"
    assert (tmp_path / API_KEY_FILENAME).read_text(encoding="utf-8") == "test-key\n"


def test_update_video_defaults_script_preserves_image_defaults(tmp_path: Path):
    config_path = tmp_path / CONFIG_FILENAME
    config_path.write_text(json.dumps(_workspace_config()), encoding="utf-8")

    script_path = SCRIPT_DIR / "update_video_defaults.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--workspace-root",
            str(tmp_path),
            "--video-t2v-duration",
            "4",
            "--videoedit-audio-setting",
            "auto",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    saved_config = json.loads(config_path.read_text(encoding="utf-8"))
    assert saved_config["defaults"]["t2i"]["size"] == "2K"
    assert saved_config["defaults"]["i2i"]["size"] == "1K"
    assert saved_config["defaults"]["video"]["t2v"]["model"] == "wan2.7-t2v"
    assert saved_config["defaults"]["video"]["t2v"]["duration"] == 4
    assert saved_config["defaults"]["video"]["videoedit"]["audio_setting"] == "auto"


def test_update_video_defaults_script_merges_existing_video_defaults(tmp_path: Path):
    config = _workspace_config()
    config["defaults"]["video"] = {
        "t2v": {
            "model": "wan2.6-t2v",
            "size": "1920*1080",
            "duration": 6,
            "prompt_extend": False,
            "watermark": True,
        },
        "i2v": {
            "model": "wan2.7-i2v",
            "resolution": "1080P",
            "duration": 8,
            "prompt_extend": False,
            "watermark": True,
        },
        "videoedit": {
            "model": "wan2.7-videoedit",
            "resolution": "1080P",
            "duration": 7,
            "prompt_extend": False,
            "watermark": True,
            "audio_setting": "auto",
        },
    }
    config_path = tmp_path / CONFIG_FILENAME
    config_path.write_text(json.dumps(config), encoding="utf-8")

    script_path = SCRIPT_DIR / "update_video_defaults.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--workspace-root",
            str(tmp_path),
            "--video-t2v-duration",
            "4",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    saved_config = json.loads(config_path.read_text(encoding="utf-8"))
    assert saved_config["defaults"]["video"]["t2v"]["size"] == "1920*1080"
    assert saved_config["defaults"]["video"]["t2v"]["duration"] == 4
    assert saved_config["defaults"]["video"]["t2v"]["watermark"] is True
    assert saved_config["defaults"]["video"]["i2v"]["duration"] == 8
    assert saved_config["defaults"]["video"]["videoedit"]["audio_setting"] == "auto"


def test_update_video_defaults_reset_replaces_video_defaults(tmp_path: Path):
    config = _workspace_config()
    config["defaults"]["video"] = {
        "t2v": {
            "model": "wan2.6-t2v",
            "size": "1920*1080",
            "duration": 6,
            "prompt_extend": False,
            "watermark": True,
        },
    }
    config_path = tmp_path / CONFIG_FILENAME
    config_path.write_text(json.dumps(config), encoding="utf-8")

    script_path = SCRIPT_DIR / "update_video_defaults.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--workspace-root",
            str(tmp_path),
            "--reset",
            "--video-t2v-duration",
            "4",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    saved_config = json.loads(config_path.read_text(encoding="utf-8"))
    assert saved_config["defaults"]["video"]["t2v"]["model"] == "wan2.7-t2v"
    assert saved_config["defaults"]["video"]["t2v"]["size"] == "1280*720"
    assert saved_config["defaults"]["video"]["t2v"]["duration"] == 4
    assert saved_config["defaults"]["video"]["t2v"]["watermark"] is False
