"""On-publish webhooks (ADR-0036): signed, bounded retries, optional.

A doorbell, not a data feed: when content enters or leaves the public
site, the configured receiver gets a minimal signed JSON payload and
rebuilds through its own channel. Failures retry three times with
backoff, are recorded, and never surface as editorial errors.
"""

import hashlib
import hmac
import json
import threading
import time
import urllib.request
from datetime import UTC, datetime
from urllib.parse import urlsplit

from cms_core import ContentStatus
from fastapi import Request

TIMEOUT_SECONDS = 10.0
BACKOFF_SECONDS = (1.0, 5.0, 25.0)


def validate_webhook_settings(url: str | None, secret: str | None) -> None:
    """A configured URL without a secret fails startup loudly — unsigned
    webhooks are not an option. HTTPS required outside loopback."""
    if url is None:
        return
    if not secret:
        raise ValueError("SARDINE_WEBHOOK_URL requires SARDINE_WEBHOOK_SECRET")
    parts = urlsplit(url)
    loopback = parts.hostname in {"127.0.0.1", "::1", "localhost"}
    if parts.scheme != "https" and not (parts.scheme == "http" and loopback):
        raise ValueError("SARDINE_WEBHOOK_URL must be https (http only for loopback)")


def signature(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def emit_transition(
    request: Request, *, kind: str, entity_id: str, before: ContentStatus, after: ContentStatus
) -> None:
    """Fire the ADR-0036 events for a saved status transition."""
    settings = request.app.state.settings
    if settings.webhook_url is None or settings.webhook_secret is None:
        return
    if after is ContentStatus.PUBLISHED and before is not ContentStatus.PUBLISHED:
        event = "published"
    elif before is ContentStatus.PUBLISHED and after is not ContentStatus.PUBLISHED:
        event = "unpublished"
    else:
        return
    payload = {
        "event": event,
        "entity": {"kind": kind, "id": entity_id},
        "occurred_at": datetime.now(UTC).isoformat(),
    }
    body = json.dumps(payload, sort_keys=True).encode("utf-8")
    app = request.app

    def run() -> None:
        headers = {
            "Content-Type": "application/json",
            "X-Sardine-Signature": signature(settings.webhook_secret, body),
        }
        # Startup validated the URL; revalidate at send time so no code
        # path can ever hand urlopen a file:// or custom scheme (B310).
        if urlsplit(settings.webhook_url).scheme not in {"https", "http"}:
            app.state.last_webhook_error = datetime.now(UTC).isoformat()
            return
        for backoff in (0.0, *BACKOFF_SECONDS):
            if backoff:
                time.sleep(backoff)
            try:
                message = urllib.request.Request(
                    settings.webhook_url, data=body, headers=headers, method="POST"
                )
                with urllib.request.urlopen(  # nosec B310 - scheme enforced above
                    message, timeout=TIMEOUT_SECONDS
                ) as answer:
                    if 200 <= answer.status < 300:
                        return
            except Exception:
                pass
        app.state.last_webhook_error = datetime.now(UTC).isoformat()

    threading.Thread(target=run, daemon=True).start()
