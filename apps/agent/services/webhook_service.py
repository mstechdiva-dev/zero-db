import hashlib
import hmac
import json
import os
import time
from typing import Optional

import httpx


class WebhookService:
    """Send HMAC-signed HTTP POST alerts to customer-configured webhook URLs.

    Always the first alert channel checked and fired before Slack, PagerDuty,
    or email. Payload is signed with HMAC-SHA256 using the shared signing
    secret so receivers can verify authenticity and reject replayed requests.
    """

    SIGNING_SECRET_ENV = "SCHEMAZERO_WEBHOOK_SIGNING_SECRET"

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url
        self._signing_secret = os.environ.get(self.SIGNING_SECRET_ENV, "")

    def _sign(self, timestamp: int, raw_body: bytes) -> str:
        """Return the HMAC-SHA256 signature as 'sha256=<hex>'."""
        message = f"{timestamp}.".encode() + raw_body
        digest = hmac.new(
            self._signing_secret.encode("utf-8"),
            message,
            hashlib.sha256,
        ).hexdigest()
        return f"sha256={digest}"

    def build_payload(
        self,
        database_name: str,
        engine: str,
        risk_level: str,
        change_type: str,
        object_type: str,
        object_name: str,
        summary: str,
        next_action: str,
        dashboard_url: str = "",
    ) -> dict:
        return {
            "event": "schema_change",
            "database_name": database_name,
            "engine": engine,
            "risk_level": risk_level,
            "change_type": change_type,
            "object_type": object_type,
            "object_name": object_name,
            "summary": summary,
            "next_action": next_action,
            "timestamp": int(time.time()),
            "dashboard_url": dashboard_url,
        }

    async def send(
        self,
        database_name: str,
        engine: str,
        risk_level: str,
        change_type: str,
        object_type: str,
        object_name: str,
        summary: str,
        next_action: str,
        dashboard_url: str = "",
    ) -> bool:
        """Send a signed webhook POST. Returns True on success.

        Retries once on failure before returning False.
        """
        if not self.webhook_url:
            return False

        payload = self.build_payload(
            database_name=database_name,
            engine=engine,
            risk_level=risk_level,
            change_type=change_type,
            object_type=object_type,
            object_name=object_name,
            summary=summary,
            next_action=next_action,
            dashboard_url=dashboard_url,
        )
        raw_body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        timestamp = int(time.time())
        signature = self._sign(timestamp, raw_body) if self._signing_secret else ""

        headers = {
            "Content-Type": "application/json",
            "SchemaZero-Timestamp": str(timestamp),
        }
        if signature:
            headers["SchemaZero-Signature"] = signature

        for attempt in range(2):
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        self.webhook_url,
                        content=raw_body,
                        headers=headers,
                        timeout=10,
                    )
                    if resp.status_code < 300:
                        return True
            except Exception:
                pass
            if attempt == 0:
                continue  # retry once

        return False
