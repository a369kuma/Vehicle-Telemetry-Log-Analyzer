import unittest

from telemetry_analyzer.analyzer import TelemetryAnalyzer
from telemetry_analyzer.parser import parse_jsonl
from telemetry_analyzer.rules import DEFAULT_SIGNAL_RANGES, DEFAULT_TRANSITION_RULES


class TelemetryAnalyzerTest(unittest.TestCase):
    def test_analyzer_flags_invalid_transitions_and_range_anomalies(self) -> None:
        lines = [
            '{"session_id":"S-1","timestamp":"2026-07-13T12:00:00Z","vehicle_id":"VH-1","signal":"gear_state","value":"PARK"}',
            '{"session_id":"S-1","timestamp":"2026-07-13T12:00:01Z","vehicle_id":"VH-1","signal":"gear_state","value":"DRIVE"}',
            '{"session_id":"S-1","timestamp":"2026-07-13T12:00:02Z","vehicle_id":"VH-1","signal":"battery_voltage","value":18.1}',
        ]

        analyzer = TelemetryAnalyzer(DEFAULT_SIGNAL_RANGES, DEFAULT_TRANSITION_RULES)
        summary = analyzer.analyze(parse_jsonl(lines))

        self.assertEqual(summary.records_seen, 3)
        self.assertEqual(summary.valid_records, 3)
        self.assertEqual(len(summary.anomalies), 2)
        self.assertIn("invalid gear_state transition", summary.anomalies[0].message)
        self.assertIn("outside expected range", summary.anomalies[1].message)

    def test_analyzer_reports_validation_issues_for_malformed_records(self) -> None:
        lines = [
            '{"session_id":"S-1","timestamp":"not-a-date","vehicle_id":"VH-1","signal":"engine_rpm"}',
            "{bad-json",
        ]

        analyzer = TelemetryAnalyzer(DEFAULT_SIGNAL_RANGES, DEFAULT_TRANSITION_RULES)
        summary = analyzer.analyze(parse_jsonl(lines))

        self.assertEqual(summary.records_seen, 2)
        self.assertEqual(summary.valid_records, 0)
        self.assertGreaterEqual(len(summary.validation_issues), 3)
        self.assertFalse(summary.anomalies)


if __name__ == "__main__":
    unittest.main()
