import http.client
import json
import threading
import unittest
from http.server import ThreadingHTTPServer

from telemetry_analyzer.api import TelemetryApiHandler, analyze_jsonl_text


class TelemetryApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), TelemetryApiHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.host, self.port = self.server.server_address

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

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

    def test_health_endpoint_returns_ok(self) -> None:
        status, payload = self._request("GET", "/health")

        self.assertEqual(status, 200)
        self.assertEqual(payload, {"status": "ok"})

    def test_analyze_endpoint_returns_summary(self) -> None:
        status, payload = self._request(
            "POST",
            "/analyze",
            {
                "log": '{"session_id":"S-10","timestamp":"2026-07-13T12:00:00Z","vehicle_id":"VH-10","signal":"battery_voltage","value":18.5}'
            },
        )

        self.assertEqual(status, 200)
        self.assertEqual(payload["records_seen"], 1)
        self.assertEqual(len(payload["anomalies"]), 1)

    def test_analyze_endpoint_accepts_custom_rules(self) -> None:
        status, payload = self._request(
            "POST",
            "/analyze",
            {
                "log": '{"session_id":"S-10","timestamp":"2026-07-13T12:00:00Z","vehicle_id":"VH-10","signal":"battery_voltage","value":18.5}',
                "rules": {
                    "signal_ranges": {
                        "battery_voltage": {
                            "minimum": 9.0,
                            "maximum": 20.0,
                        }
                    }
                },
            },
        )

        self.assertEqual(status, 200)
        self.assertEqual(payload["records_seen"], 1)
        self.assertEqual(payload["anomalies"], [])

    def test_analyze_endpoint_rejects_invalid_rules(self) -> None:
        status, payload = self._request(
            "POST",
            "/analyze",
            {
                "log": "",
                "rules": {
                    "signal_ranges": {
                        "battery_voltage": {
                            "minimum": 20.0,
                            "maximum": 10.0,
                        }
                    }
                },
            },
        )

        self.assertEqual(status, 400)
        self.assertIn("minimum cannot exceed maximum", payload["error"])

    def test_analyze_endpoint_rejects_invalid_body(self) -> None:
        status, payload = self._request("POST", "/analyze", {"log": ["not", "text"]})

        self.assertEqual(status, 400)
        self.assertEqual(payload, {"error": "field 'log' must contain JSONL text"})

    def test_unknown_endpoint_returns_not_found(self) -> None:
        status, payload = self._request("GET", "/missing")

        self.assertEqual(status, 404)
        self.assertEqual(payload, {"error": "not_found"})

    def _request(
        self,
        method: str,
        path: str,
        body: dict[str, object] | None = None,
    ) -> tuple[int, dict[str, object]]:
        connection = http.client.HTTPConnection(self.host, self.port, timeout=5)
        encoded_body = None
        headers = {}
        if body is not None:
            encoded_body = json.dumps(body)
            headers["Content-Type"] = "application/json"

        try:
            connection.request(method, path, body=encoded_body, headers=headers)
            response = connection.getresponse()
            payload = json.loads(response.read().decode("utf-8"))
            return response.status, payload
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
