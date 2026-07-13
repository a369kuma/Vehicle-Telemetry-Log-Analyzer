from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from telemetry_analyzer.analyzer import AnalysisSummary, TelemetryAnalyzer
from telemetry_analyzer.parser import parse_jsonl
from telemetry_analyzer.rules import DEFAULT_SIGNAL_RANGES, DEFAULT_TRANSITION_RULES


def summary_to_dict(summary: AnalysisSummary) -> dict[str, Any]:
    return {
        "records_seen": summary.records_seen,
        "valid_records": summary.valid_records,
        "validation_issues": [issue.__dict__ for issue in summary.validation_issues],
        "anomalies": [anomaly.__dict__ for anomaly in summary.anomalies],
    }


def analyze_jsonl_text(payload: str) -> dict[str, Any]:
    analyzer = TelemetryAnalyzer(DEFAULT_SIGNAL_RANGES, DEFAULT_TRANSITION_RULES)
    summary = analyzer.analyze(parse_jsonl(payload.splitlines()))
    return summary_to_dict(summary)


class TelemetryApiHandler(BaseHTTPRequestHandler):
    server_version = "TelemetryAnalyzer/0.1"

    def do_GET(self) -> None:
        if self.path != "/health":
            self._write_json(404, {"error": "not_found"})
            return

        self._write_json(200, {"status": "ok"})

    def do_POST(self) -> None:
        if self.path != "/analyze":
            self._write_json(404, {"error": "not_found"})
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length).decode("utf-8")
        try:
            request_body = json.loads(raw_body)
        except json.JSONDecodeError:
            self._write_json(400, {"error": "request body must be JSON"})
            return

        log_text = request_body.get("log")
        if not isinstance(log_text, str):
            self._write_json(400, {"error": "field 'log' must contain JSONL text"})
            return

        self._write_json(200, analyze_jsonl_text(log_text))

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _write_json(self, status_code: int, payload: dict[str, Any]) -> None:
        response = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the telemetry analyzer REST API.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    server = ThreadingHTTPServer((args.host, args.port), TelemetryApiHandler)
    print(f"telemetry analyzer API listening on http://{args.host}:{args.port}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
