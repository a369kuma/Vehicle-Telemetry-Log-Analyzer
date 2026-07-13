from __future__ import annotations

import argparse
import json
from pathlib import Path

from telemetry_analyzer.api import summary_to_dict
from telemetry_analyzer.analyzer import TelemetryAnalyzer
from telemetry_analyzer.parser import parse_jsonl
from telemetry_analyzer.rules import DEFAULT_SIGNAL_RANGES, DEFAULT_TRANSITION_RULES, load_rules_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze vehicle telemetry JSONL logs.")
    parser.add_argument("log_file", type=Path, help="Path to a newline-delimited JSON telemetry log.")
    parser.add_argument(
        "--rules",
        type=Path,
        help="Optional JSON rules file for custom signal bounds and transition rules.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        signal_ranges, transition_rules = (
            load_rules_file(args.rules) if args.rules else (DEFAULT_SIGNAL_RANGES, DEFAULT_TRANSITION_RULES)
        )
    except ValueError as exc:
        parser.error(str(exc))

    analyzer = TelemetryAnalyzer(signal_ranges, transition_rules)
    with args.log_file.open("r", encoding="utf-8") as log_stream:
        summary = analyzer.analyze(parse_jsonl(log_stream))

    print(
        json.dumps(
            summary_to_dict(summary),
            indent=2,
            sort_keys=True,
        )
    )
    return 1 if summary.validation_issues or summary.anomalies else 0


if __name__ == "__main__":
    raise SystemExit(main())
