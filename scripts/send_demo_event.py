#!/usr/bin/env python3
"""Demo event emitter: a NovaOps-compatible producer for the Sentinel ingest route.

This is a stand-in for the upstream monitoring process, not that process. It speaks
the machine contract (one event, one stable event id, bearer access) so the whole
loop can be demonstrated from the producer's side: OBSERVE -> UNDERSTAND -> DECIDE
-> approval -> simulated ACT -> VERIFY -> AUDIT.

Usage:
    export SENTINEL_INGEST_TOKEN=...      # runtime only, never a command-line value
    python scripts/send_demo_event.py
    python scripts/send_demo_event.py --url http://127.0.0.1:8000 --event-id my-evt-1

Re-sending the same event id costs nothing: the route replays the incident it
already made instead of running the model a second time.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_URL = "http://127.0.0.1:8000"
INGEST_PATH = "/api/v1/events/ingest"

FIELDS = ("event_id", "incident_id", "workflow_state", "duplicate", "console_path")


def build_event(event_id: str) -> dict:
    """One operational event in the shape a monitoring producer would send."""
    return {
        "event_id": event_id,
        "source": "novaops",
        "event_type": "ram_high",
        "title": "API latency spike",
        "description": "p95 latency increased from 180ms to 2.4s",
        "severity_hint": "warning",
        "evidence": [
            "error rate increased to 8.2%",
            "CPU increased to 91%",
            "memory pressure reported by the host agent",
        ],
    }


def post(url: str, body: dict, bearer: str) -> tuple[int, dict]:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {bearer}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        # Inference is synchronous and can take tens of seconds, so the caller's
        # budget has to exceed the provider read timeout rather than the reverse.
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as refused:
        raw = refused.read().decode("utf-8", "replace")
        try:
            return refused.code, json.loads(raw)
        except json.JSONDecodeError:
            return refused.code, {"detail": raw}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Send one demo operational event.")
    parser.add_argument("--url", default=os.environ.get("SENTINEL_URL", DEFAULT_URL))
    parser.add_argument("--event-id", default="novaops-demo-0001")
    args = parser.parse_args(argv)

    bearer = os.environ.get("SENTINEL_INGEST_TOKEN", "").strip()
    if not bearer:
        sys.stderr.write("SENTINEL_INGEST_TOKEN is not set; export it and retry.\n")
        raise SystemExit(2)

    status, payload = post(args.url.rstrip("/") + INGEST_PATH, build_event(args.event_id), bearer)
    print(f"HTTP {status}")
    if status >= 400:
        print(json.dumps(payload.get("detail", payload), indent=2))
        return 1
    for field in FIELDS:
        print(f"{field}: {payload.get(field)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
