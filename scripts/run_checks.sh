#!/usr/bin/env bash
set -euo pipefail

PYTHONPATH=src python3 -m unittest discover -s tests
make cpp-validator

set +e
validator_output=$(./build/telemetry_validator examples/sample_telemetry.jsonl)
status=$?
set -e

echo "$validator_output"

if [[ "$status" -ne 2 ]]; then
  echo "expected sample telemetry to exit with anomaly status 2, got $status" >&2
  exit 1
fi

if [[ "$validator_output" != *"anomalies=2"* ]]; then
  echo "expected sample telemetry to report two anomalies" >&2
  exit 1
fi

set +e
malformed_output=$(./build/telemetry_validator tests/fixtures/malformed_telemetry.jsonl)
malformed_status=$?
set -e

echo "$malformed_output"

if [[ "$malformed_status" -ne 1 ]]; then
  echo "expected malformed telemetry to exit with validation status 1, got $malformed_status" >&2
  exit 1
fi

if [[ "$malformed_output" != *"field=record"* ]]; then
  echo "expected malformed telemetry to report a record-level validation issue" >&2
  exit 1
fi
