# Vehicle Telemetry Log Analyzer

A backend workflow for ingesting vehicle telemetry logs, validating structured
records, checking expected signal behavior, and flagging abnormal state
transitions across repeated test sessions.

## Current capabilities

- Parse newline-delimited JSON telemetry logs.
- Validate required telemetry fields and value types.
- Check numeric signals against configured ranges.
- Detect invalid state transitions per vehicle signal.
- Produce a compact analysis summary from the command line.
- Expose analysis through a lightweight REST API.
- Provide PostgreSQL schema and Docker Compose services for local integration.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Analyze a log file:

```bash
telemetry-analyzer examples/sample_telemetry.jsonl
```

Run the standard local checks:

```bash
./scripts/run_checks.sh
```

Build and run the C++ validator directly:

```bash
make cpp-validator
./build/telemetry_validator examples/sample_telemetry.jsonl
```

Run the API and PostgreSQL stack:

```bash
docker compose up --build
```

Analyze logs over HTTP:

```bash
curl -X POST http://localhost:8080/analyze \
  -H "Content-Type: application/json" \
  -d '{"log":"{\"session_id\":\"S-100\",\"timestamp\":\"2026-07-13T12:00:00Z\",\"vehicle_id\":\"VH-42\",\"signal\":\"battery_voltage\",\"value\":18.2}"}'
```

## Log format

Each line is a JSON object:

```json
{"session_id":"S-100","timestamp":"2026-07-13T12:00:00Z","vehicle_id":"VH-42","signal":"gear_state","value":"PARK"}
```
