import os
import httpx


class SlackService:
    """Send formatted Slack alerts via Incoming Webhook. Full implementation in Phase 7."""

    def __init__(self, webhook_url: str | None = None):
        self.webhook_url = webhook_url or os.environ.get("SLACK_WEBHOOK_URL", "")

    async def send_alert(self, risk_level: str, payload: dict) -> bool:
        """Send a risk alert to Slack. Returns True on success."""
        if not self.webhook_url:
            return False
        # Full Block Kit formatting implemented in Phase 7
        async with httpx.AsyncClient() as client:
            response = await client.post(self.webhook_url, json=payload, timeout=10)
            return response.status_code == 200
