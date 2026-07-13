from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


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


def rules_from_mapping(payload: dict[str, Any]) -> tuple[dict[str, SignalRange], TransitionRuleSet]:
    signal_ranges = dict(DEFAULT_SIGNAL_RANGES)
    transition_rules = {
        signal: {state: set(next_values) for state, next_values in rules.items()}
        for signal, rules in DEFAULT_TRANSITION_RULES.allowed.items()
    }

    configured_ranges = payload.get("signal_ranges", {})
    if configured_ranges is not None and not isinstance(configured_ranges, dict):
        raise ValueError("signal_ranges must be an object")

    for signal, bounds in configured_ranges.items():
        if not isinstance(signal, str):
            raise ValueError("signal range names must be strings")
        if not isinstance(bounds, dict):
            raise ValueError(f"signal_ranges.{signal} must be an object")

        try:
            minimum = float(bounds["minimum"])
            maximum = float(bounds["maximum"])
        except KeyError as exc:
            raise ValueError(f"signal_ranges.{signal} missing {exc.args[0]}") from exc
        except (TypeError, ValueError) as exc:
            raise ValueError(f"signal_ranges.{signal} bounds must be numeric") from exc

        if minimum > maximum:
            raise ValueError(f"signal_ranges.{signal} minimum cannot exceed maximum")

        signal_ranges[signal] = SignalRange(minimum, maximum)

    configured_transitions = payload.get("transition_rules", {})
    if configured_transitions is not None and not isinstance(configured_transitions, dict):
        raise ValueError("transition_rules must be an object")

    for signal, states in configured_transitions.items():
        if not isinstance(signal, str):
            raise ValueError("transition rule names must be strings")
        if not isinstance(states, dict):
            raise ValueError(f"transition_rules.{signal} must be an object")

        signal_rules = transition_rules.setdefault(signal, {})
        for state, allowed_next in states.items():
            if not isinstance(state, str):
                raise ValueError(f"transition_rules.{signal} states must be strings")
            if not isinstance(allowed_next, list) or not all(isinstance(value, str) for value in allowed_next):
                raise ValueError(f"transition_rules.{signal}.{state} must be a list of strings")
            signal_rules[state] = set(allowed_next)

    return signal_ranges, TransitionRuleSet(transition_rules)


def load_rules_file(path: Path) -> tuple[dict[str, SignalRange], TransitionRuleSet]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} is not valid JSON: {exc.msg}") from exc

    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")

    return rules_from_mapping(payload)
