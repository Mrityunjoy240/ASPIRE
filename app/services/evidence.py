# app/services/evidence.py
# DEC-01 (approved): persisted InterventionPlan.evidence is a JSON array of
# structured entries — the canonical schema is documented in
# docs/05_DATA_API_CONTRACTS.md ("Evidence entry contract"). The LLM/agent
# layer only ever produces list[str] (CONSTITUTION A-05 parse format,
# 10_TASKS supervisor step 4); conversion into canonical entries happens at
# this boundary and REQUIRES backend-verified provenance: `source` and
# `timestamp` are never invented, defaulted, clocked at write time, or taken
# from model output. Typed backend values keep their type (numbers stay
# numbers, booleans stay booleans) — they are not stringified.

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator


@dataclass(frozen=True)
class EvidenceProvenance:
    """Backend-verified provenance for evidence items.

    Supplied only by the producer (engine/service) that actually observed the
    fact — never by the LLM, never defaulted by the conversion boundary.
    """

    source: str
    timestamp: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("provenance source must be a non-empty string")
        if not isinstance(self.timestamp, datetime) or self.timestamp.tzinfo is None:
            raise ValueError("provenance timestamp must be a timezone-aware datetime")


class EvidenceEntry(BaseModel):
    """Canonical persisted evidence entry (DEC-01 / 05_DATA_API_CONTRACTS)."""

    # Exactly the five approved fields; extras are rejected so presentation
    # hints or model-invented keys can never leak into the persisted contract.
    model_config = ConfigDict(extra="forbid")

    id: str  # stable identity — UUID string (existing project id convention)
    label: str  # non-empty human-readable caption
    value: str | int | float | bool  # typed scalar, preserved as-is
    source: str  # verified provenance label (backend source / approved metadata)
    timestamp: datetime  # provenance time, ISO-8601 with UTC offset

    @field_validator("id")
    @classmethod
    def _id_must_be_uuid(cls, v: str) -> str:
        try:
            UUID(v)
        except (ValueError, AttributeError, TypeError) as exc:
            raise ValueError("entry id must be a UUID string") from exc
        return v

    @field_validator("label", "source")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must be a non-empty string")
        return v

    @field_validator("value", mode="before")
    @classmethod
    def _value_must_be_scalar(cls, v: Any) -> Any:
        # The union's smart mode matches str/int/float/bool inputs exactly
        # (no coercion), so a backend 75.0 stays float instead of becoming a
        # string; this validator rejects non-scalars outright and also rejects
        # NaN/inf, which are not valid JSON scalars.
        if not isinstance(v, (str, int, float, bool)):
            raise ValueError("value must be a string, number, or boolean")
        if isinstance(v, float) and not isfinite(v):
            raise ValueError("value must be a finite number")
        return v

    @field_validator("timestamp")
    @classmethod
    def _timestamp_must_be_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware (ISO-8601 with offset)")
        return v


def validate_evidence_entries(raw: Any) -> list[EvidenceEntry]:
    """Validate a persisted/canonical evidence array.

    Accepts an array of entry objects (possibly already JSON round-tripped).
    Raises ValueError for a non-array payload or duplicate ids, and pydantic
    ValidationError for malformed entries.
    """
    if not isinstance(raw, list):
        raise ValueError("evidence must be an array of structured entries")
    entries = [EvidenceEntry.model_validate(item) for item in raw]
    ids = [entry.id for entry in entries]
    if len(ids) != len(set(ids)):
        raise ValueError("evidence entry ids must be unique")
    return entries


def dump_evidence_entries(entries: Sequence[EvidenceEntry]) -> list[dict[str, Any]]:
    """Serialize validated entries to the JSON-ready canonical array."""
    return [entry.model_dump(mode="json") for entry in entries]


def _split_label_value(text: str) -> tuple[str, str]:
    """Presentation-only normalization of an LLM evidence string.

    Splits "Label: value" on the first ": " so the rendered entry mirrors the
    label/value presentation of the plan UI. Purely display formatting — it
    never touches types or provenance. Without a separator the whole string
    is both label and value.
    """
    if ": " in text:
        label, _, value = text.partition(": ")
        label, value = label.strip(), value.strip()
        if label and value:
            return label, value
    return text, text


def convert_llm_evidence(
    llm_evidence: Sequence[str],
    *,
    provenance: EvidenceProvenance | None,
) -> list[dict[str, Any]]:
    """Conversion boundary: LLM/agent `list[str]` -> canonical persisted entries.

    Provenance is mandatory and backend-supplied; without it the conversion
    refuses (ValueError) instead of inventing `source`/`timestamp`. Unsupported
    items (non-string, blank) also raise — nothing is silently dropped or
    backfilled, so no fabricated metadata can ever be produced.

    LLM strings remain strings here (they carry no typed origin); producers
    with typed backend facts should call `build_evidence_entry` instead.
    """
    if provenance is None:
        raise ValueError(
            "evidence provenance is required: source and timestamp must come "
            "from verified backend provenance, never from the model"
        )
    out: list[dict[str, Any]] = []
    for item in llm_evidence:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"unsupported LLM evidence item: {item!r}")
        label, value = _split_label_value(item.strip())
        entry = EvidenceEntry(
            id=str(uuid4()),
            label=label,
            value=value,
            source=provenance.source,
            timestamp=provenance.timestamp,
        )
        out.append(entry.model_dump(mode="json"))
    return out


def build_evidence_entry(
    label: str,
    value: str | int | float | bool,
    *,
    provenance: EvidenceProvenance,
) -> dict[str, Any]:
    """Producer-side builder for backend-typed evidence facts.

    Preserves the original value type: 75.0 stays float, 3 stays int,
    True stays boolean. Identity follows the project UUID convention.
    """
    entry = EvidenceEntry(
        id=str(uuid4()),
        label=label,
        value=value,
        source=provenance.source,
        timestamp=provenance.timestamp,
    )
    return entry.model_dump(mode="json")


__all__ = [
    "EvidenceEntry",
    "EvidenceProvenance",
    "ValidationError",
    "build_evidence_entry",
    "convert_llm_evidence",
    "dump_evidence_entries",
    "validate_evidence_entries",
]
