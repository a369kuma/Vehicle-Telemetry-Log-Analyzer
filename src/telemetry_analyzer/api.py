from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from telemetry_analyzer.analyzer import AnalysisSummary, TelemetryAnalyzer
from telemetry_analyzer.parser import parse_jsonl
from telemetry_analyzer.rules import (
    DEFAULT_SIGNAL_RANGES,
    DEFAULT_TRANSITION_RULES,
    SignalRange,
    TransitionRuleSet,
    load_rules_file,
    rules_from_mapping,
)


def summary_to_dict(summary: AnalysisSummary) -> dict[str, Any]:
    return {
        "records_seen": summary.records_seen,
        "valid_records": summary.valid_records,
        "validation_issues": [issue.__dict__ for issue in summary.validation_issues],
        "anomalies": [anomaly.__dict__ for anomaly in summary.anomalies],
    }


def analyze_jsonl_text(
    payload: str,
    rules: dict[str, Any] | None = None,
    default_signal_ranges: dict[str, SignalRange] | None = None,
    default_transition_rules: TransitionRuleSet | None = None,
) -> dict[str, Any]:
    base_signal_ranges = default_signal_ranges or DEFAULT_SIGNAL_RANGES
    base_transition_rules = default_transition_rules or DEFAULT_TRANSITION_RULES
    signal_ranges, transition_rules = (
        rules_from_mapping(rules) if rules is not None else (base_signal_ranges, base_transition_rules)
    )
    analyzer = TelemetryAnalyzer(signal_ranges, transition_rules)
    summary = analyzer.analyze(parse_jsonl(payload.splitlines()))
    return summary_to_dict(summary)


class TelemetryApiHandler(BaseHTTPRequestHandler):
    server_version = "TelemetryAnalyzer/0.1"
    default_signal_ranges = DEFAULT_SIGNAL_RANGES
    default_transition_rules = DEFAULT_TRANSITION_RULES

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

        rules = request_body.get("rules")
        if rules is not None and not isinstance(rules, dict):
            self._write_json(400, {"error": "field 'rules' must be an object when provided"})
            return

        try:
            self._write_json(
                200,
                analyze_jsonl_text(
                    log_text,
                    rules,
                    self.default_signal_ranges,
                    self.default_transition_rules,
                ),
            )
        except ValueError as exc:
            self._write_json(400, {"error": str(exc)})

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
    parser.add_argument(
        "--rules",
        type=str,
        help="Optional JSON rules file used as the API default when requests omit rules.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.rules:
        signal_ranges, transition_rules = load_rules_file(Path(args.rules))
        TelemetryApiHandler.default_signal_ranges = signal_ranges
        TelemetryApiHandler.default_transition_rules = transition_rules
    server = ThreadingHTTPServer((args.host, args.port), TelemetryApiHandler)
    print(f"telemetry analyzer API listening on http://{args.host}:{args.port}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
