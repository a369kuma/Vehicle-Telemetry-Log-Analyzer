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

## Log format

Each line is a JSON object:

```json
{"session_id":"S-100","timestamp":"2026-07-13T12:00:00Z","vehicle_id":"VH-42","signal":"gear_state","value":"PARK"}
```
