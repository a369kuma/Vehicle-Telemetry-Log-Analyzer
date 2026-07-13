from __future__ import annotations

import argparse
import json
from pathlib import Path

from telemetry_analyzer.api import summary_to_dict
from telemetry_analyzer.analyzer import TelemetryAnalyzer
from telemetry_analyzer.parser import parse_jsonl
from telemetry_analyzer.rules import DEFAULT_SIGNAL_RANGES, DEFAULT_TRANSITION_RULES


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze vehicle telemetry JSONL logs.")
    parser.add_argument("log_file", type=Path, help="Path to a newline-delimited JSON telemetry log.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    analyzer = TelemetryAnalyzer(DEFAULT_SIGNAL_RANGES, DEFAULT_TRANSITION_RULES)
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
