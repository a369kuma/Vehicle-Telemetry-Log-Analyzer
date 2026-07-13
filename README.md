# Vehicle Telemetry Log Analyzer

A backend lab for catching suspicious vehicle telemetry before it disappears
into a mountain of log files.

The analyzer reads newline-delimited JSON telemetry, validates each record,
checks signals against expected ranges, and flags weird state transitions across
repeated test sessions. It includes a Python analysis workflow, a C++ validator,
a lightweight REST API, PostgreSQL schema, Docker Compose wiring, and a Bash
check script for repeatable local runs.

In other words: feed it test-drive telemetry, and it points at the lines that
deserve a second look.

## Current capabilities

- Parse newline-delimited JSON telemetry logs without needing a database first.
- Validate required fields, timestamp shape, malformed JSON, and missing values.
- Check numeric signals such as `battery_voltage`, `engine_rpm`, and `vehicle_speed`.
- Detect invalid state transitions such as `PARK -> DRIVE`.
- Flag duplicate or backwards timestamps per session and vehicle.
- Produce compact CLI output for automated checks.
- Expose the same analysis through a small REST API.
- Provide a C++ validator for fast local validation paths.
- Include PostgreSQL schema and Docker Compose services for integration work.

## What it catches

The sample log intentionally contains bad telemetry:

```json
{"session_id":"S-100","timestamp":"2026-07-13T12:00:01Z","vehicle_id":"VH-42","signal":"gear_state","value":"DRIVE"}
{"session_id":"S-100","timestamp":"2026-07-13T12:00:02Z","vehicle_id":"VH-42","signal":"battery_voltage","value":18.2}
```

The analyzer reports:

- `gear_state` jumped from `PARK` straight to `DRIVE`.
- `battery_voltage` exceeded the expected `9.0..16.0` range.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
./scripts/run_checks.sh
```

That command runs the Python tests, builds the C++ validator, checks the sample
anomaly log, and verifies malformed-input handling.

## Try it

```bash
telemetry-analyzer examples/sample_telemetry.jsonl
```

The sample exits with a non-zero status on purpose because it contains
anomalies. That makes it useful for testing alert paths, CI checks, and parser
behavior.

Run the full local check suite any time:

```bash
./scripts/run_checks.sh
```

## C++ Validator

Build and run the dependency-free validator directly:

```bash
make cpp-validator
./build/telemetry_validator examples/sample_telemetry.jsonl
```

It supports flat telemetry JSON objects and reports validation/anomaly counts in
a shell-friendly format.

## REST API And Local Stack

Run the API with PostgreSQL available:

```bash
docker compose up --build
```

Analyze logs over HTTP:

```bash
curl -X POST http://localhost:8080/analyze \
  -H "Content-Type: application/json" \
  -d '{"log":"{\"session_id\":\"S-100\",\"timestamp\":\"2026-07-13T12:00:00Z\",\"vehicle_id\":\"VH-42\",\"signal\":\"battery_voltage\",\"value\":18.2}"}'
```

Health check:

```bash
curl http://localhost:8080/health
```

## Log format

Each line is a JSON object:

```json
{"session_id":"S-100","timestamp":"2026-07-13T12:00:00Z","vehicle_id":"VH-42","signal":"gear_state","value":"PARK"}
```

Required fields:

- `session_id`: repeated test-session identifier.
- `timestamp`: ISO-8601 UTC timestamp ending in `Z`.
- `vehicle_id`: vehicle or bench identifier.
- `signal`: telemetry signal name.
- `value`: numeric or string signal value.

## Known limitations

- The REST API returns analysis results but does not yet persist records or anomalies to PostgreSQL.
- The C++ validator intentionally supports flat telemetry JSON objects and rejects nested JSON values.
- Signal ranges and transition rules are currently compiled into the application instead of loaded from external configuration.
