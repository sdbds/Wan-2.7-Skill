from __future__ import annotations

import json
import re
from pathlib import Path


PORTRAIT_DATA_DIR = Path(__file__).resolve().parents[1] / "references" / "portrait-data"
TRIGGERS_FILE = PORTRAIT_DATA_DIR / "triggers_by_dim.json"
CARRIERS_FILE = PORTRAIT_DATA_DIR / "carriers.json"


def _load_portrait_data() -> tuple[dict[str, list[str]], list[dict[str, object]]]:
    triggers = json.loads(TRIGGERS_FILE.read_text(encoding="utf-8"))
    carriers_doc = json.loads(CARRIERS_FILE.read_text(encoding="utf-8"))
    return triggers, carriers_doc["carriers"]


def test_portrait_data_files_exist_and_parse():
    triggers, carriers = _load_portrait_data()

    assert triggers
    assert carriers


def test_gender_and_age_are_split_dimensions():
    triggers, _ = _load_portrait_data()

    assert triggers["J0_性别"] == ["女性", "男性"]
    assert "青年（18-30岁）" in triggers["J1_年龄段"]
    assert "J1_性别年龄" not in triggers


def test_each_carrier_template_placeholders_match_slots():
    _, carriers = _load_portrait_data()

    for carrier in carriers:
        placeholders = set(re.findall(r"\{([^{}]+)\}", carrier["template"]))
        slots = set(carrier.get("slots", []))
        assert placeholders == slots, carrier["carrier_id"]


def test_carrier_slots_resolve_to_valid_typed_option_sources():
    triggers, carriers = _load_portrait_data()

    for carrier in carriers:
        slot_source = carrier.get("slot_source", {})

        for slot in carrier.get("slots", []):
            source = slot_source.get(slot)
            if source is None:
                assert slot in triggers, (carrier["carrier_id"], slot)
                continue

            assert isinstance(source, dict), (carrier["carrier_id"], slot, type(source).__name__)
            kind = source["kind"]

            if kind == "literal_values":
                values = source["values"]
                assert values, (carrier["carrier_id"], slot)
                assert all(isinstance(item, str) and item for item in values), (
                    carrier["carrier_id"],
                    slot,
                )
                continue

            if kind == "dim_union":
                dims = source["dims"]
                assert dims, (carrier["carrier_id"], slot)
                for dim_name in dims:
                    assert dim_name in triggers, (carrier["carrier_id"], slot, dim_name)
                    assert triggers[dim_name], (carrier["carrier_id"], slot, dim_name)
                continue

            if kind == "filtered_dim":
                picked_dim = source["dim"]
                assert picked_dim in triggers, (carrier["carrier_id"], slot, picked_dim)
                values = source["values"]
                assert values, (carrier["carrier_id"], slot)
                for value in values:
                    assert value in triggers[picked_dim], (carrier["carrier_id"], slot, value)
                continue

            raise AssertionError((carrier["carrier_id"], slot, kind))


def test_each_carrier_has_selection_metadata():
    _, carriers = _load_portrait_data()

    allowed_depths = {"quick", "standard", "deep"}

    for carrier in carriers:
        assert carrier["build_depth"] in allowed_depths, carrier["carrier_id"]
        assert carrier["use_cases"], carrier["carrier_id"]
        assert all(isinstance(use_case, str) and use_case for use_case in carrier["use_cases"]), carrier["carrier_id"]


def test_fixed_values_are_valid_trigger_members():
    triggers, carriers = _load_portrait_data()

    for carrier in carriers:
        for dim_name, raw_values in carrier.get("fixed", {}).items():
            assert dim_name in triggers, (carrier["carrier_id"], dim_name)
            values = raw_values if isinstance(raw_values, list) else [raw_values]
            for value in values:
                assert value in triggers[dim_name], (carrier["carrier_id"], dim_name, value)
