# SPEC-1 API Reference

Base URL: `http://localhost:8000` (default)

All responses are JSON. Errors follow `{"detail": "..."}` (FastAPI default).
Paginated endpoints return `{"total": N, "limit": N, "offset": N, "items": [...]}`.

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

Returns signals from the OSINT store.

Query params:
- `limit` (int, default 20, max 200)
- `offset` (int, default 0)
- `source_type` (str, optional) — filter by source type (e.g. `"RSS"`, `"API"`)

```json
{
  "total": 142,
  "limit": 20,
  "offset": 0,
  "items": [
    {
      "signal_id": "sig_...",
      "source": "war_on_the_rocks",
      "source_type": "RSS",
      "title": "...",
      "url": "...",
      "published_at": "2026-05-06T12:00:00Z",
      "word_count": 1240
    }
  ]
}
```

### `POST /signals/ingest`

Accept an external signal, score it, and enqueue for pipeline processing. Returns immediately (202).

```json
{"signal_id": "sig_...", "status": "queued"}
```

---

## Intelligence Records

### `GET /intel`

Returns scored and analyzed intelligence records.

Query params:
- `limit` (int, default 20, max 200)
- `offset` (int, default 0)
- `classification` (str, optional) — filter by classification (e.g. `"Corroborated"`, `"Escalate"`)
- `min_confidence` (float, default 0.0) — filter by confidence floor

```json
{
  "total": 37,
  "limit": 20,
  "offset": 0,
  "items": [
    {
      "record_id": "rec_...",
      "run_id": "run_...",
      "signal_id": "sig_...",
      "classification": "Corroborated",
      "confidence": 0.87,
      "domain": "cyber",
      "pattern": "...",
      "generated_at": "2026-05-06T06:01:00Z"
    }
  ]
}
```

---

## Leads

### `GET /leads`

Returns stored intelligence leads.

Query params:
- `limit` (int, default 20, max 200)
- `offset` (int, default 0)
- `priority` (str, optional) — filter by priority (`HIGH`, `MEDIUM`, `LOW`)
- `category` (str, optional) — filter by category

### `POST /leads/generate`

Generate leads from current intelligence records and store them. No request body.

Query params:
- `max_leads` (int, default 50, max 200)

```json
{"generated": 12, "stored": 12}
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

Returns stored PsyOp detection scores.

Query params:
- `limit` (int, default 20, max 200)
- `offset` (int, default 0)
- `classification` (str, optional) — filter by classification (e.g. `"HIGH"`, `"MEDIUM"`)

### `POST /psyop/analyse`

Score a single text snippet for PsyOp patterns. Saves the result.

Request body: `{"text": "..."}`

### `POST /psyop/run`

Run PsyOp detection over all current OSINT records.

```json
{"processed": 58, "flagged": 3}
```

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

### `GET /calibration/report`

Returns the current calibration report (accuracy by classification, confidence buckets).
Descriptive only — never auto-applies tuning.

```json
{
  "generated_at": "...",
  "overall_accuracy": 0.74,
  "by_classification": {...},
  "reliability_buckets": {...}
}
```

### `GET /calibration/proposals`

Returns suggested threshold adjustments. Descriptive only — never auto-applied.

Query params:
- `sample_floor` (int, default 5) — minimum verdicts to consider a bucket
- `delta_floor` (float, default 0.15) — minimum drift to surface an adjustment

```json
{
  "generated_at": "...",
  "suggested_adjustments": [...]
}
```

---

## Cycle

### `POST /cycle/run`

Triggers a full pipeline cycle synchronously. Returns when complete.

```json
{
  "run_id": "run_...",
  "started_at": "2026-05-06T06:00:00Z",
  "finished_at": "2026-05-06T06:01:23Z",
  "signals_harvested": 42,
  "signals_parsed": 42,
  "opportunities_found": 11,
  "investigations_generated": 11,
  "outcomes_verified": 11,
  "records_stored": 9,
  "errors": []
}
```

### `GET /cycle/status`

Returns the status and result of the last cycle run.

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
| `SPEC1_ENVIRONMENT` | `production` | Runtime environment tag |
| `SPEC1_LOG_LEVEL` | `INFO` | Logging verbosity |
