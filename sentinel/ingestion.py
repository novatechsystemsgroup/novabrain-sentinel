"""Machine event ingestion: the bearer-token front door and its idempotency ledger.

Nothing here analyses an incident or decides an approval. The module authenticates
a producer, then answers one question: has this exact event already been paid for?
"""

import hmac
import logging
import os
import threading

from fastapi import Request

TOKEN_ENV = "SENTINEL_INGEST_TOKEN"

# A replay guard, not a history. Sized like the workflow store so the two bounded
# in-memory surfaces expire at the same rate.
MAX_TRACKED_EVENTS = 200

INGEST_ERROR_STATUS = {
    "invalid_ingest_token": 401,
    "ingest_not_configured": 503,
    "event_in_progress": 409,
    "ingest_ledger_full": 503,
}

logger = logging.getLogger("sentinel.ingestion")


class IngestError(Exception):
    """A refusal at the ingestion front door, carrying its documented status code."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class EventInProgress(IngestError):
    def __init__(self, event_id: str):
        super().__init__(
            "event_in_progress",
            f"Event '{event_id}' is already being analysed. Retry once it has finished.",
        )


def resolve_token() -> str:
    token = os.environ.get(TOKEN_ENV, "").strip()
    if not token:
        raise IngestError(
            "ingest_not_configured",
            f"Machine ingestion is not configured: set {TOKEN_ENV} to enable it.",
        )
    return token


def bearer_token(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    scheme, _, supplied = header.partition(" ")
    if scheme.lower() != "bearer":
        return None
    return supplied.strip() or None


def require_ingest_token(request: Request) -> None:
    """Guard the machine route. Runs before the body is read, so an unauthenticated
    caller learns nothing about the event schema."""
    expected = resolve_token()
    supplied = bearer_token(request)
    if supplied is None or not hmac.compare_digest(
        supplied.encode("utf-8"), expected.encode("utf-8")
    ):
        raise IngestError("invalid_ingest_token", "A valid bearer ingest token is required.")


class IdempotencyLedger:
    """Bounded, per-process memory of which producer events were already handled.

    An entry is either a claim (the event is being analysed) or a result (the event
    produced this incident). Claims are never dropped: losing one would let a second
    request pay for a duplicate inference. A replay counts as recent use, so eviction
    takes the finished entries nobody is replaying any more.
    """

    def __init__(self, capacity: int = MAX_TRACKED_EVENTS):
        if capacity < 1:
            raise ValueError("capacity must be at least 1")
        self.capacity = capacity
        self._entries: dict[str, str | None] = {}
        self._lock = threading.Lock()

    def reserve(self, event_id: str) -> str | None:
        """None when the caller owns the analysis; else the incident already made.

        Raises EventInProgress when the same event is mid-flight.
        """
        with self._lock:
            if event_id in self._entries:
                incident_id = self._entries.pop(event_id)
                if incident_id is None:
                    self._entries[event_id] = None
                    raise EventInProgress(event_id)
                self._entries[event_id] = incident_id
                return incident_id
            self._make_room()
            self._entries[event_id] = None
            return None

    def complete(self, event_id: str, incident_id: str) -> None:
        with self._lock:
            self._entries[event_id] = incident_id

    def release(self, event_id: str) -> None:
        """Give up a claim so a producer can retry after a failed inference."""
        with self._lock:
            if self._entries.get(event_id) is None:
                self._entries.pop(event_id, None)

    def discard(self, event_id: str) -> bool:
        """Forget a finished entry whose incident is no longer in the store."""
        with self._lock:
            if self._entries.get(event_id) is None:
                return False
            del self._entries[event_id]
            return True

    def _make_room(self) -> None:
        if len(self._entries) < self.capacity:
            return
        for event_id, incident_id in self._entries.items():
            if incident_id is not None:
                self._entries.pop(event_id)
                logger.info("evicted finished event %s", event_id)
                return
        raise IngestError(
            "ingest_ledger_full",
            (
                f"The idempotency ledger holds {self.capacity} events and none of them "
                "has finished. Events being analysed are never evicted; this slice "
                "keeps the ledger in memory, so a restart is the reset."
            ),
        )
