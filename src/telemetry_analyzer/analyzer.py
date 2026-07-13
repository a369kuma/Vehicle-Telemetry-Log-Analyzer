from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterable

from telemetry_analyzer.models import TelemetryRecord
from telemetry_analyzer.rules import SignalRange, TransitionRuleSet
from telemetry_analyzer.validation import ValidationIssue, validate_record


@dataclass(frozen=True)
class SignalAnomaly:
    line_number: int
    session_id: str
    vehicle_id: str
    signal: str
    value: object
    message: str


@dataclass
class AnalysisSummary:
    records_seen: int = 0
    validation_issues: list[ValidationIssue] = field(default_factory=list)
    anomalies: list[SignalAnomaly] = field(default_factory=list)

    @property
    def valid_records(self) -> int:
        return self.records_seen - len({issue.line_number for issue in self.validation_issues})


class TelemetryAnalyzer:
    def __init__(
        self,
        signal_ranges: dict[str, SignalRange] | None = None,
        transition_rules: TransitionRuleSet | None = None,
    ) -> None:
        self.signal_ranges = signal_ranges or {}
        self.transition_rules = transition_rules or TransitionRuleSet()

    def analyze(self, records: Iterable[TelemetryRecord]) -> AnalysisSummary:
        summary = AnalysisSummary()
        last_values: dict[tuple[str, str, str], object] = {}
        seen_timestamps: dict[tuple[str, str], list[str]] = defaultdict(list)

        for record in records:
            summary.records_seen += 1
            issues = validate_record(record)
            summary.validation_issues.extend(issues)
            if issues:
                continue

            self._check_signal_range(record, summary)
            self._check_transition(record, last_values, summary)
            seen_timestamps[(record.session_id, record.vehicle_id)].append(record.timestamp)

        return summary

    def _check_signal_range(self, record: TelemetryRecord, summary: AnalysisSummary) -> None:
        signal_range = self.signal_ranges.get(record.signal)
        if signal_range is None:
            return

        if not signal_range.contains(record.value):
            summary.anomalies.append(
                SignalAnomaly(
                    line_number=record.line_number,
                    session_id=record.session_id,
                    vehicle_id=record.vehicle_id,
                    signal=record.signal,
                    value=record.value,
                    message=f"{record.signal} outside expected range {signal_range.minimum}..{signal_range.maximum}",
                )
            )

    def _check_transition(
        self,
        record: TelemetryRecord,
        last_values: dict[tuple[str, str, str], object],
        summary: AnalysisSummary,
    ) -> None:
        key = (record.session_id, record.vehicle_id, record.signal)
        previous = last_values.get(key)
        last_values[key] = record.value

        if previous is None:
            return

        if not self.transition_rules.is_allowed(record.signal, previous, record.value):
            summary.anomalies.append(
                SignalAnomaly(
                    line_number=record.line_number,
                    session_id=record.session_id,
                    vehicle_id=record.vehicle_id,
                    signal=record.signal,
                    value=record.value,
                    message=f"invalid {record.signal} transition {previous!r} -> {record.value!r}",
                )
            )
