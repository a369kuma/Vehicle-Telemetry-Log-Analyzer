import unittest

from telemetry_analyzer.api import analyze_jsonl_text


class TelemetryApiTest(unittest.TestCase):
    def test_analyze_jsonl_text_returns_serializable_summary(self) -> None:
        result = analyze_jsonl_text(
            "\n".join(
                [
                    '{"session_id":"S-9","timestamp":"2026-07-13T12:00:00Z","vehicle_id":"VH-9","signal":"engine_rpm","value":9001}',
                    '{"session_id":"S-9","timestamp":"2026-07-13T12:00:01Z","vehicle_id":"VH-9","signal":"engine_rpm","value":750}',
                ]
            )
        )

        self.assertEqual(result["records_seen"], 2)
        self.assertEqual(result["valid_records"], 2)
        self.assertEqual(len(result["anomalies"]), 1)
        self.assertEqual(result["validation_issues"], [])


if __name__ == "__main__":
    unittest.main()
