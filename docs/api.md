# SPEC-1 API Reference

Base URL: `http://localhost:8000` (default)

All responses are JSON. Errors follow `{"detail": "..."}` (FastAPI default).

---

## Health

### `GET /health`

Returns service health and scheduler status.

```json
{"status": "ok", "scheduler": "running"}
```

---

## Signals

### `GET /signals`

Returns recently harvested signals.

Query params:
- `limit` (int, default 50) — max records to return
- `source` (str, optional) — filter by source name

```json
[
  {
    "signal_id": "sig_...",
    "source": "war_on_the_rocks",
    "title": "...",
    "url": "...",
    "published_at": "2026-05-06T12:00:00Z",
    "word_count": 1240
  }
]
```

---

## Intelligence Records

### `GET /intel`

Returns scored and analyzed intelligence records.

Query params:
- `limit` (int, default 50)
- `min_confidence` (float, optional) — filter by confidence floor
- `outcome` (str, optional) — filter by outcome classification

```json
[
  {
    "record_id": "rec_...",
    "run_id": "run_...",
    "signal_id": "sig_...",
    "outcome": "Corroborated",
    "confidence": 0.87,
    "domain": "cyber",
    "pattern": "...",
    "generated_at": "2026-05-06T06:01:00Z"
  }
]
```

---

## Leads

### `GET /leads`

Returns actionable intelligence leads.

### `POST /leads`

Create a lead manually.

Request body:
```json
{
  "title": "...",
  "summary": "...",
  "priority": "high",
  "source_record_ids": ["rec_..."]
}
```

---

## World Brief

### `GET /brief`

Returns the latest daily world intelligence brief.

```json
{
  "brief_id": "brief_...",
  "date": "2026-05-06",
  "headline": "...",
  "sections": [...],
  "sources": [...],
  "confidence": 0.81
}
```

---

## PsyOp Detection

### `GET /psyop`

Returns psychological-operation detection results.

Query params:
- `limit` (int, default 50)
- `min_score` (float, optional)

---

## FARA

### `GET /fara`

Returns Foreign Agents Registration Act filing records.

---

## Verdicts

### `GET /verdicts`

Returns filed human verdicts.

Query params:
- `record_id` (str, optional) — filter by intelligence record

### `POST /verdicts`

File a human verdict on a record.

Request body:
```json
{
  "record_id": "rec_...",
  "kind": "correct",
  "reviewer": "analyst_handle",
  "notes": "..."
}
```

`kind` must be one of: `correct`, `incorrect`, `partial`, `unclear`

---

## Calibration

### `GET /calibration`

Returns the calibration drift report. Descriptive only — never auto-applies tuning.

```json
{
  "generated_at": "...",
  "overall_accuracy": 0.74,
  "by_classification": {...},
  "reliability_buckets": {...},
  "suggested_adjustments": [...]
}
```

---

## Cycle

### `POST /cycle/run`

Triggers an immediate full pipeline cycle. Returns cycle metadata on completion.

```json
{"run_id": "run_...", "status": "complete", "records_produced": 7}
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | Required for verification and briefing |
| `SPEC1_STORE_PATH` | `spec1_intelligence.jsonl` | Intelligence record store |
| `SPEC1_DB_PATH` | `spec1.db` | SQLite database path |
| `SPEC1_API_HOST` | `0.0.0.0` | API bind address |
| `SPEC1_API_PORT` | `8000` | API port |
| `SPEC1_CRON_HOUR` | `6` | Scheduled cycle hour (24h) |
| `SPEC1_CRON_MINUTE` | `0` | Scheduled cycle minute |
| `SPEC1_TIMEZONE` | `America/Los_Angeles` | Scheduler timezone |
| `SPEC1_FEED_TIMEOUT` | `15` | Feed fetch timeout (seconds) |
| `SPEC1_QUANT_ENABLED` | `false` | Enable quantitative market pipeline |
| `SPEC1_ENVIRONMENT` | `production` | Runtime environment tag |
| `SPEC1_LOG_LEVEL` | `INFO` | Logging verbosity |
