from __future__ import annotations

import sys
from pathlib import Path

import pytest


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from build_request import InvalidJobSpecError, JobSpec, build_request_payload


def _job(*, images: list[str], bbox_list: list[list[list[int]]]) -> JobSpec:
    return JobSpec(
        prompt="Edit the boxed region naturally.",
        images=images,
        parameters={"bbox_list": bbox_list},
        source_dir=Path.cwd(),
    )


def test_single_image_bbox_is_forwarded():
    payload, warnings = build_request_payload(
        _job(
            images=["https://example.com/ref-1.png"],
            bbox_list=[[[10, 20, 30, 40]]],
        )
    )

    assert warnings == []
    assert payload["parameters"]["bbox_list"] == [[[10, 20, 30, 40]]]


def test_multi_image_bbox_alignment_is_preserved():
    payload, _ = build_request_payload(
        _job(
            images=[
                "https://example.com/ref-1.png",
                "https://example.com/ref-2.png",
            ],
            bbox_list=[[], [[50, 60, 70, 80]]],
        )
    )

    assert payload["parameters"]["bbox_list"] == [[], [[50, 60, 70, 80]]]


def test_bbox_requires_input_images():
    with pytest.raises(InvalidJobSpecError, match="bbox_list is only valid when input images are provided"):
        build_request_payload(
            _job(
                images=[],
                bbox_list=[[[10, 20, 30, 40]]],
            )
        )


def test_bbox_list_length_must_match_image_count():
    with pytest.raises(InvalidJobSpecError, match="bbox_list length must equal the number of input images"):
        build_request_payload(
            _job(
                images=[
                    "https://example.com/ref-1.png",
                    "https://example.com/ref-2.png",
                ],
                bbox_list=[[[10, 20, 30, 40]]],
            )
        )


def test_each_image_accepts_at_most_two_boxes():
    with pytest.raises(InvalidJobSpecError, match="supports at most 2 boxes"):
        build_request_payload(
            _job(
                images=["https://example.com/ref-1.png"],
                bbox_list=[[[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]],
            )
        )


def test_box_must_have_four_coordinates():
    with pytest.raises(InvalidJobSpecError, match="must be \\[x1, y1, x2, y2\\]"):
        build_request_payload(
            _job(
                images=["https://example.com/ref-1.png"],
                bbox_list=[[[10, 20, 30]]],
            )
        )


def test_box_coordinates_must_be_non_negative_and_ordered():
    with pytest.raises(InvalidJobSpecError, match="must satisfy x1 < x2 and y1 < y2"):
        build_request_payload(
            _job(
                images=["https://example.com/ref-1.png"],
                bbox_list=[[[30, 40, 10, 20]]],
            )
        )

    with pytest.raises(InvalidJobSpecError, match="must use non-negative coordinates"):
        build_request_payload(
            _job(
                images=["https://example.com/ref-1.png"],
                bbox_list=[[[0, -1, 10, 20]]],
            )
        )
