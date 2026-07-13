import json
import tempfile
import unittest
from pathlib import Path

from telemetry_analyzer.analyzer import TelemetryAnalyzer
from telemetry_analyzer.parser import parse_jsonl
from telemetry_analyzer.rules import load_rules_file, rules_from_mapping


class RulesTest(unittest.TestCase):
    def test_rules_from_mapping_overrides_signal_bounds(self) -> None:
        signal_ranges, transition_rules = rules_from_mapping(
            {
                "signal_ranges": {
                    "battery_voltage": {
                        "minimum": 9.0,
                        "maximum": 20.0,
                    }
                }
            }
        )
        analyzer = TelemetryAnalyzer(signal_ranges, transition_rules)
        summary = analyzer.analyze(
            parse_jsonl(
                [
                    '{"session_id":"S-1","timestamp":"2026-07-13T12:00:00Z","vehicle_id":"VH-1","signal":"battery_voltage","value":18.2}'
                ]
            )
        )

        self.assertEqual(summary.anomalies, [])

    def test_rules_from_mapping_overrides_transition_rules(self) -> None:
        signal_ranges, transition_rules = rules_from_mapping(
            {
                "transition_rules": {
                    "gear_state": {
                        "PARK": ["PARK", "DRIVE"],
                    }
                }
            }
        )
        analyzer = TelemetryAnalyzer(signal_ranges, transition_rules)
        summary = analyzer.analyze(
            parse_jsonl(
                [
                    '{"session_id":"S-1","timestamp":"2026-07-13T12:00:00Z","vehicle_id":"VH-1","signal":"gear_state","value":"PARK"}',
                    '{"session_id":"S-1","timestamp":"2026-07-13T12:00:01Z","vehicle_id":"VH-1","signal":"gear_state","value":"DRIVE"}',
                ]
            )
        )

        self.assertEqual(summary.anomalies, [])

    def test_transition_rule_overrides_preserve_omitted_default_states(self) -> None:
        _, transition_rules = rules_from_mapping(
            {
                "transition_rules": {
                    "gear_state": {
                        "PARK": ["PARK", "DRIVE"],
                    }
                }
            }
        )

        self.assertTrue(transition_rules.is_allowed("gear_state", "DRIVE", "NEUTRAL"))

    def test_load_rules_file_rejects_invalid_bounds(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rules.json"
            path.write_text(
                json.dumps(
                    {
                        "signal_ranges": {
                            "battery_voltage": {
                                "minimum": 20,
                                "maximum": 10,
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "minimum cannot exceed maximum"):
                load_rules_file(path)


if __name__ == "__main__":
    unittest.main()
