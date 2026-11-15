# tests/test_evidence_contract.py
# DEC-01 (approved): canonical structured evidence entries.
# Validation contract, provenance rules (no fabrication), the LLM list[str]
# conversion boundary, typed-value preservation, and identity convention.
# Live JSONB round trip: tests/test_intervention_plan_jsonb_pg.py.

from datetime import UTC, datetime
from math import inf, nan
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.services.evidence import (
    EvidenceProvenance,
    build_evidence_entry,
    convert_llm_evidence,
    dump_evidence_entries,
    validate_evidence_entries,
)

PROV = EvidenceProvenance(
    source="attendance_derived_state",
    timestamp=datetime(2026, 10, 7, 8, 0, tzinfo=UTC),
)


def _valid_entry(**overrides):
    entry = {
        "id": str(uuid4()),
        "label": "Attendance",
        "value": "73.3%",
        "source": "attendance_derived_state",
        "timestamp": "2026-10-07T08:00:00+00:00",
    }
    entry.update(overrides)
    return entry


# --- validation: valid structured evidence passes ---

def test_valid_entry_passes_validation():
    entries = validate_evidence_entries([_valid_entry()])
    assert len(entries) == 1
    assert entries[0].label == "Attendance"
    assert entries[0].timestamp == datetime(2026, 10, 7, 8, 0, tzinfo=UTC)


def test_empty_evidence_array_is_valid():
    assert validate_evidence_entries([]) == []


def test_typed_values_pass_and_are_preserved():
    for value in (72.5, 3, True, "73.3%"):
        (entry,) = validate_evidence_entries([_valid_entry(value=value)])
        assert entry.value == value
        assert type(entry.value) is type(value)


def test_entry_with_datetime_object_passes():
    (entry,) = validate_evidence_entries(
        [_valid_entry(timestamp=datetime(2026, 10, 7, 8, 0, tzinfo=UTC))]
    )
    assert entry.timestamp.tzinfo is not None


# --- validation: missing or malformed required fields are rejected ---

@pytest.mark.parametrize("field", ["id", "label", "value", "source", "timestamp"])
def test_missing_required_field_is_rejected(field):
    payload = _valid_entry()
    del payload[field]
    with pytest.raises(ValidationError):
        validate_evidence_entries([payload])


def test_non_array_evidence_is_rejected():
    with pytest.raises(ValueError, match="array of structured entries"):
        validate_evidence_entries({"id": str(uuid4())})
    with pytest.raises(ValueError, match="array of structured entries"):
        validate_evidence_entries(None)


def test_non_object_entry_is_rejected():
    with pytest.raises(ValidationError):
        validate_evidence_entries(["attendance 73%"])


def test_unknown_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        validate_evidence_entries([_valid_entry(confidence="HIGH")])


def test_non_uuid_id_is_rejected():
    with pytest.raises(ValidationError, match="UUID"):
        validate_evidence_entries([_valid_entry(id="e1")])  # presentation-only ref


def test_duplicate_ids_are_rejected():
    entry_id = str(uuid4())
    with pytest.raises(ValueError, match="unique"):
        validate_evidence_entries(
            [_valid_entry(id=entry_id), _valid_entry(id=entry_id, label="Other")]
        )


def test_empty_label_or_source_is_rejected():
    with pytest.raises(ValidationError):
        validate_evidence_entries([_valid_entry(label="   ")])
    with pytest.raises(ValidationError):
        validate_evidence_entries([_valid_entry(source="")])


# --- validation: invalid timestamps and unsupported values are rejected ---

def test_invalid_timestamp_string_is_rejected():
    with pytest.raises(ValidationError):
        validate_evidence_entries([_valid_entry(timestamp="not-a-date")])


def test_naive_timestamp_is_rejected():
    with pytest.raises(ValidationError, match="timezone-aware"):
        validate_evidence_entries([_valid_entry(timestamp="2026-10-07T08:00:00")])


@pytest.mark.parametrize("value", [{"a": 1}, ["a"], None, nan, inf])
def test_unsupported_value_types_are_rejected(value):
    with pytest.raises(ValidationError):
        validate_evidence_entries([_valid_entry(value=value)])


def test_numeric_value_is_not_coerced_to_string():
    # smart union keeps numbers as numbers instead of stringifying them
    (entry,) = validate_evidence_entries([_valid_entry(value=75.0)])
    assert isinstance(entry.value, float)
    assert entry.value == 75.0


# --- LLM list[str] conversion boundary ---

def test_llm_list_converts_to_canonical_entries():
    result = convert_llm_evidence(
        ["Attendance: 73.3%", "Threshold: 75%", "Exam in 8 days"],
        provenance=PROV,
    )
    assert len(result) == 3
    entries = validate_evidence_entries(result)
    assert entries[0].label == "Attendance"
    assert entries[0].value == "73.3%"
    assert entries[1].label == "Threshold"
    assert entries[2].label == "Exam in 8 days"  # no separator -> whole string
    assert entries[2].value == "Exam in 8 days"
    for entry in entries:
        assert entry.source == "attendance_derived_state"  # backend provenance
        assert entry.timestamp == PROV.timestamp
        UUID(entry.id)  # stable identity follows the UUID convention


def test_conversion_ids_are_unique():
    result = convert_llm_evidence(["A: 1", "B: 2"], provenance=PROV)
    assert len({entry["id"] for entry in result}) == 2


def test_conversion_of_empty_list_returns_empty_array():
    assert convert_llm_evidence([], provenance=PROV) == []


def test_conversion_without_provenance_is_refused():
    # No source/timestamp may ever be invented for model output.
    with pytest.raises(ValueError, match="provenance is required"):
        convert_llm_evidence(["Attendance: 73.3%"], provenance=None)


def test_conversion_with_bad_provenance_is_refused():
    with pytest.raises(ValueError, match="provenance source"):
        convert_llm_evidence(
            ["x"],
            provenance=EvidenceProvenance(source="  ", timestamp=PROV.timestamp),
        )
    with pytest.raises(ValueError, match="timezone-aware"):
        convert_llm_evidence(
            ["x"],
            provenance=EvidenceProvenance(source="s", timestamp=datetime(2026, 1, 1)),
        )


@pytest.mark.parametrize("bad", ["", "   ", None, 42])
def test_conversion_rejects_unsupported_items_without_fabrication(bad):
    with pytest.raises(ValueError, match="unsupported LLM evidence item"):
        convert_llm_evidence(["ok", bad], provenance=PROV)


def test_conversion_failure_produces_no_partial_fabricated_output():
    # The call raises; nothing is returned, so no metadata exists at all.
    with pytest.raises(ValueError):
        convert_llm_evidence(["good", ""], provenance=PROV)


# --- typed backend evidence (no stringification) ---

def test_build_entry_preserves_typed_values():
    float_entry = build_evidence_entry("Attendance", 72.5, provenance=PROV)
    int_entry = build_evidence_entry("Required to recover", 3, provenance=PROV)
    bool_entry = build_evidence_entry("Critical band", True, provenance=PROV)
    str_entry = build_evidence_entry("Exam", "8 days", provenance=PROV)
    assert float_entry["value"] == 72.5 and type(float_entry["value"]) is float
    assert int_entry["value"] == 3 and type(int_entry["value"]) is int
    assert bool_entry["value"] is True
    assert str_entry["value"] == "8 days"
    for payload in (float_entry, int_entry, bool_entry, str_entry):
        assert payload["source"] == PROV.source
        assert payload["timestamp"].startswith("2026-10-07T08:00:00")
        UUID(payload["id"])
        validate_evidence_entries([payload])


def test_dump_is_json_serializable_and_revalidates():
    import json

    payload = build_evidence_entry("Attendance", 72.5, provenance=PROV)
    text = json.dumps([payload])
    restored = validate_evidence_entries(json.loads(text))
    assert restored[0].value == 72.5
    assert dump_evidence_entries(restored) == [payload]


# --- identity convention ---

def test_entry_ids_are_uuid4_shaped_and_stable_on_validated_input():
    entry_id = str(uuid4())
    (entry,) = validate_evidence_entries([_valid_entry(id=entry_id)])
    assert entry.id == entry_id
    built = build_evidence_entry("x", "y", provenance=PROV)
    assert UUID(built["id"]).version == 4
