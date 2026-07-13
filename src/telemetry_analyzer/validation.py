from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from telemetry_analyzer.models import TelemetryRecord


@dataclass(frozen=True)
class ValidationIssue:
    line_number: int
    field: str
    message: str


def validate_record(record: TelemetryRecord) -> list[ValidationIssue]:
    if record.parse_error is not None:
        return [ValidationIssue(record.line_number, "record", record.parse_error)]

    issues: list[ValidationIssue] = []
    required_fields = {
        "session_id": record.session_id,
        "timestamp": record.timestamp,
        "vehicle_id": record.vehicle_id,
        "signal": record.signal,
    }

    for field_name, value in required_fields.items():
        if not isinstance(value, str) or not value.strip():
            issues.append(ValidationIssue(record.line_number, field_name, "required non-empty string"))

    if record.value is None:
        issues.append(ValidationIssue(record.line_number, "value", "required"))

    if record.timestamp and not _is_iso8601_utc(record.timestamp):
        issues.append(ValidationIssue(record.line_number, "timestamp", "expected ISO-8601 UTC timestamp"))

    return issues


def _is_iso8601_utc(value: str) -> bool:
    if not value.endswith("Z"):
        return False

    try:
        datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError:
        return False
    return True
