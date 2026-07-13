from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SignalRange:
    minimum: float
    maximum: float

    def contains(self, value: object) -> bool:
        if not isinstance(value, (int, float)):
            return False
        return self.minimum <= float(value) <= self.maximum


@dataclass(frozen=True)
class TransitionRuleSet:
    allowed: dict[str, dict[object, set[object]]] = field(default_factory=dict)

    def is_allowed(self, signal: str, previous: object, current: object) -> bool:
        signal_rules = self.allowed.get(signal)
        if signal_rules is None:
            return True

        allowed_next_values = signal_rules.get(previous)
        if allowed_next_values is None:
            return True

        return current in allowed_next_values


DEFAULT_SIGNAL_RANGES = {
    "battery_voltage": SignalRange(9.0, 16.0),
    "engine_rpm": SignalRange(0.0, 8000.0),
    "vehicle_speed": SignalRange(0.0, 260.0),
}

DEFAULT_TRANSITION_RULES = TransitionRuleSet(
    {
        "gear_state": {
            "PARK": {"PARK", "REVERSE", "NEUTRAL"},
            "REVERSE": {"REVERSE", "NEUTRAL", "PARK"},
            "NEUTRAL": {"NEUTRAL", "DRIVE", "REVERSE", "PARK"},
            "DRIVE": {"DRIVE", "NEUTRAL"},
        },
        "ignition_state": {
            "OFF": {"OFF", "ACCESSORY"},
            "ACCESSORY": {"ACCESSORY", "ON", "OFF"},
            "ON": {"ON", "START", "OFF"},
            "START": {"ON"},
        },
    }
)
