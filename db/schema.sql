CREATE TABLE IF NOT EXISTS telemetry_sessions (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS telemetry_records (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES telemetry_sessions(session_id),
    recorded_at TIMESTAMPTZ NOT NULL,
    vehicle_id TEXT NOT NULL,
    signal TEXT NOT NULL,
    value_json JSONB NOT NULL,
    source_line INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_telemetry_records_session_vehicle
    ON telemetry_records(session_id, vehicle_id);

CREATE INDEX IF NOT EXISTS idx_telemetry_records_signal_time
    ON telemetry_records(signal, recorded_at);

CREATE TABLE IF NOT EXISTS telemetry_anomalies (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES telemetry_sessions(session_id),
    vehicle_id TEXT NOT NULL,
    signal TEXT NOT NULL,
    source_line INTEGER NOT NULL,
    message TEXT NOT NULL,
    value_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
