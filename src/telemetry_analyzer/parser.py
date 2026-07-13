from __future__ import annotations

import json
from collections.abc import Iterable, Iterator

from telemetry_analyzer.models import TelemetryRecord


def parse_jsonl(lines: Iterable[str]) -> Iterator[TelemetryRecord]:
    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue

        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError as exc:
            yield TelemetryRecord(
                line_number=line_number,
                session_id="",
                timestamp="",
                vehicle_id="",
                signal="",
                value=None,
                parse_error=f"invalid JSON: {exc.msg}",
            )
            continue

        yield TelemetryRecord(
            line_number=line_number,
            session_id=payload.get("session_id", ""),
            timestamp=payload.get("timestamp", ""),
            vehicle_id=payload.get("vehicle_id", ""),
            signal=payload.get("signal", ""),
            value=payload.get("value"),
        )
