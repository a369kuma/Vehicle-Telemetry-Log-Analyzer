from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TelemetryRecord:
    line_number: int
    session_id: str
    timestamp: str
    vehicle_id: str
    signal: str
    value: Any
