# Scripts

Operational helpers that sit outside the service. They are demo and verification tooling, not
part of the request path.

| Script | What it does |
|---|---|
| `send_demo_event.py` | Demo event emitter — a **NovaOps-compatible producer**, not a NovaOps integration. Posts one operational event to `POST /api/v1/events/ingest` so the whole loop can be demonstrated from the producer's side. Stdlib only. Reads `SENTINEL_INGEST_TOKEN` from the environment (never a CLI argument, never printed) and targets `--url`, defaulting to `SENTINEL_URL` then `http://127.0.0.1:8000` |

```bash
export SENTINEL_INGEST_TOKEN=$(openssl rand -hex 32)   # runtime only
.venv/bin/python scripts/send_demo_event.py --url http://127.0.0.1:8000
```

Re-running it with the same `event_id` costs nothing: the route replays the incident it already
made instead of paying for a second inference.
