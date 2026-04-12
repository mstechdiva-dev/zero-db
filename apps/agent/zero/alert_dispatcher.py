"""Alert Dispatcher — routes schema change alerts to configured channels.

Channels are fired in this order (per zero.md):
  1. Custom webhook (always first if configured)
  2. Slack (HIGH and CRITICAL only)
  3. PagerDuty (CRITICAL only)
  4. Email (based on org notify_on settings)

Every alert attempt (success or failure) is written to notification_log.
A channel failure does not prevent subsequent channels from firing.
"""

import logging
import os
import time
from typing import Optional

from services.webhook_service import WebhookService
from services.slack_service import SlackService
from services.pagerduty_service import PagerDutyService
from services.email_service import EmailService

logger = logging.getLogger(__name__)

DASHBOARD_BASE_URL = os.environ.get("DASHBOARD_URL", "https://app.schemazero.com")


class AlertDispatcher:
    def __init__(self, supabase_client):
        self.supabase = supabase_client

    async def dispatch(
        self,
        org_id: str,
        change_event: dict,
        impact: dict,
        risk_level: str,
    ) -> None:
        """Fire all configured alert channels for this org and risk level."""
        alert_config = await self._get_alert_config(org_id)
        notify_on: list[str] = alert_config.get("notify_on", ["high", "critical"])

        if risk_level.lower() not in [n.lower() for n in notify_on]:
            logger.debug(
                "Skipping alerts for risk_level=%s (org_id=%s not subscribed)",
                risk_level,
                org_id,
            )
            return

        object_name = change_event.get("object_name", "unknown")
        engine = change_event.get("engine", "unknown")
        change_type = change_event.get("change_type", "schema_change")
        object_type = change_event.get("object_type", "object")
        summary = impact.get("summary", "")
        next_action = impact.get("next_action", "")
        dashboard_url = f"{DASHBOARD_BASE_URL}/dashboard"
        event_id = change_event.get("id", "")

        # Look up the actual database display name from connected_databases
        database_name = await self._get_database_name(
            change_event.get("database_id", ""), org_id
        )

        # 1. Custom webhook — always first
        webhook_url = alert_config.get("webhook_url")
        await self._fire_webhook(
            org_id=org_id,
            event_id=event_id,
            webhook_url=webhook_url,
            database_name=database_name,
            engine=engine,
            risk_level=risk_level,
            change_type=change_type,
            object_type=object_type,
            summary=summary,
            next_action=next_action,
            dashboard_url=dashboard_url,
        )

        # 2. Slack — HIGH and CRITICAL
        if risk_level.lower() in ("high", "critical"):
            slack_url = alert_config.get("slack_webhook_url")
            await self._fire_slack(
                org_id=org_id,
                event_id=event_id,
                slack_url=slack_url,
                risk_level=risk_level,
                database_name=database_name,
                engine=engine,
                change_type=change_type,
                object_type=object_type,
                object_name=object_name,
                summary=summary,
                next_action=next_action,
                dashboard_url=dashboard_url,
            )

        # 3. PagerDuty — CRITICAL only
        if risk_level.lower() == "critical":
            pd_key = alert_config.get("pagerduty_api_key")
            await self._fire_pagerduty(
                org_id=org_id,
                event_id=event_id,
                api_key=pd_key,
                database_name=database_name,
                summary=summary,
                next_action=next_action,
            )

        # 4. Email — based on notify_on config
        email_recipients: list[str] = alert_config.get("email_recipients", [])
        if email_recipients:
            await self._fire_email(
                org_id=org_id,
                event_id=event_id,
                recipients=email_recipients,
                risk_level=risk_level,
                database_name=database_name,
                engine=engine,
                change_type=change_type,
                summary=summary,
                next_action=next_action,
                dashboard_url=dashboard_url,
            )

    # ------------------------------------------------------------------
    # Individual channel fire methods
    # ------------------------------------------------------------------

    async def _fire_webhook(
        self,
        org_id: str,
        event_id: str,
        webhook_url: Optional[str],
        **kwargs,
    ) -> None:
        svc = WebhookService(webhook_url=webhook_url)
        try:
            success = await svc.send(**kwargs)
        except Exception as exc:
            logger.error("Webhook send error: %s", exc)
            success = False
        await self._log(org_id, event_id, "webhook", success)

    async def _fire_slack(
        self,
        org_id: str,
        event_id: str,
        slack_url: Optional[str],
        risk_level: str,
        database_name: str,
        engine: str,
        change_type: str,
        object_type: str,
        object_name: str,
        summary: str,
        next_action: str,
        dashboard_url: str,
    ) -> None:
        svc = SlackService(webhook_url=slack_url)
        payload = _build_slack_payload(
            risk_level=risk_level,
            database_name=database_name,
            engine=engine,
            change_type=change_type,
            object_type=object_type,
            object_name=object_name,
            summary=summary,
            next_action=next_action,
            dashboard_url=dashboard_url,
        )
        try:
            success = await svc.send_alert(risk_level=risk_level, payload=payload)
        except Exception as exc:
            logger.error("Slack send error: %s", exc)
            success = False
        await self._log(org_id, event_id, "slack", success)

    async def _fire_pagerduty(
        self,
        org_id: str,
        event_id: str,
        api_key: Optional[str],
        database_name: str,
        summary: str,
        next_action: str,
    ) -> None:
        svc = PagerDutyService(api_key=api_key)
        title = f"SchemaZero: Critical schema change in {database_name}"
        body = f"{summary}\n\n{next_action}"
        try:
            success = await svc.create_incident(title=title, body=body)
        except Exception as exc:
            logger.error("PagerDuty send error: %s", exc)
            success = False
        await self._log(org_id, event_id, "pagerduty", success)

    async def _fire_email(
        self,
        org_id: str,
        event_id: str,
        recipients: list[str],
        risk_level: str,
        database_name: str,
        engine: str,
        change_type: str,
        summary: str,
        next_action: str,
        dashboard_url: str,
    ) -> None:
        svc = EmailService()
        subject = f"[SchemaZero] {risk_level.upper()} schema change in {database_name}"
        html_body = _build_email_html(
            risk_level=risk_level,
            database_name=database_name,
            engine=engine,
            change_type=change_type,
            summary=summary,
            next_action=next_action,
            dashboard_url=dashboard_url,
        )
        try:
            success = await svc.send_alert(
                recipients=recipients, subject=subject, html_body=html_body
            )
        except Exception as exc:
            logger.error("Email send error: %s", exc)
            success = False
        await self._log(org_id, event_id, "email", success)

    async def _log(
        self,
        org_id: str,
        change_event_id: str,
        channel: str,
        success: bool,
    ) -> None:
        try:
            self.supabase.table("notification_log").insert(
                {
                    "org_id": org_id,
                    "change_event_id": change_event_id,
                    "channel": channel,
                    "success": success,
                    "sent_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
            ).execute()
        except Exception as exc:
            logger.warning("Failed to write notification_log: %s", exc)

    async def _get_database_name(self, database_id: str, org_id: str) -> str:
        """Look up the display name of a connected database."""
        if not database_id:
            return "unknown database"
        try:
            result = (
                self.supabase.table("connected_databases")
                .select("display_name")
                .eq("id", database_id)
                .eq("org_id", org_id)
                .single()
                .execute()
            )
            return result.data.get("display_name", "unknown database") if result.data else "unknown database"
        except Exception:
            return "unknown database"

    async def _get_alert_config(self, org_id: str) -> dict:
        try:
            result = (
                self.supabase.table("alert_configs")
                .select("*")
                .eq("org_id", org_id)
                .single()
                .execute()
            )
            return result.data or {}
        except Exception:
            return {}


# ---------------------------------------------------------------------------
# Payload builders
# ---------------------------------------------------------------------------

def _build_slack_payload(
    risk_level: str,
    database_name: str,
    engine: str,
    change_type: str,
    object_type: str,
    object_name: str,
    summary: str,
    next_action: str,
    dashboard_url: str,
) -> dict:
    is_critical = risk_level.lower() == "critical"
    header_text = (
        f":rotating_light: CRITICAL Schema Change — Immediate Attention Required"
        if is_critical
        else f":warning: Schema Change Detected — {risk_level.upper()} RISK"
    )

    return {
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": header_text, "emoji": True},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Database:*\n{database_name}"},
                    {"type": "mrkdwn", "text": f"*Engine:*\n{engine.capitalize()}"},
                    {"type": "mrkdwn", "text": f"*Change:*\n{change_type.replace('_', ' ').title()}"},
                    {"type": "mrkdwn", "text": f"*Object:*\n{object_type} `{object_name}`"},
                ],
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Impact Summary:*\n{summary}"},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Next Action:*\n{next_action}"},
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View in Dashboard"},
                        "url": dashboard_url,
                        "style": "primary" if not is_critical else "danger",
                    }
                ],
            },
        ]
    }


def _build_email_html(
    risk_level: str,
    database_name: str,
    engine: str,
    change_type: str,
    summary: str,
    next_action: str,
    dashboard_url: str,
) -> str:
    risk_colors = {
        "low": "#22c55e",
        "medium": "#f59e0b",
        "high": "#ef4444",
        "critical": "#dc2626",
    }
    color = risk_colors.get(risk_level.lower(), "#6b7280")

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>SchemaZero Alert</title></head>
<body style="background:#0a0a0a;color:#e5e7eb;font-family:system-ui,sans-serif;margin:0;padding:40px 20px;">
  <div style="max-width:600px;margin:0 auto;">
    <div style="border-left:4px solid {color};padding-left:16px;margin-bottom:24px;">
      <h1 style="color:{color};font-size:20px;margin:0 0 4px;">
        {risk_level.upper()} Schema Change Detected
      </h1>
      <p style="color:#9ca3af;margin:0;font-size:14px;">{database_name} · {engine.capitalize()}</p>
    </div>

    <div style="background:#111;border:1px solid #1f2937;border-radius:8px;padding:20px;margin-bottom:16px;">
      <p style="color:#9ca3af;font-size:12px;text-transform:uppercase;letter-spacing:0.05em;margin:0 0 8px;">What Changed</p>
      <p style="margin:0;font-size:15px;">{change_type.replace("_", " ").title()}</p>
    </div>

    <div style="background:#111;border:1px solid #1f2937;border-radius:8px;padding:20px;margin-bottom:16px;">
      <p style="color:#9ca3af;font-size:12px;text-transform:uppercase;letter-spacing:0.05em;margin:0 0 8px;">Impact</p>
      <p style="margin:0;font-size:15px;">{summary}</p>
    </div>

    <div style="background:#111;border:1px solid {color};border-radius:8px;padding:20px;margin-bottom:24px;">
      <p style="color:{color};font-size:12px;text-transform:uppercase;letter-spacing:0.05em;margin:0 0 8px;">Next Action</p>
      <p style="margin:0;font-size:15px;font-weight:600;">{next_action}</p>
    </div>

    <a href="{dashboard_url}"
       style="display:inline-block;background:#00e87a;color:#000;font-weight:700;
              padding:12px 24px;border-radius:8px;text-decoration:none;font-size:14px;">
      View in Dashboard
    </a>

    <p style="color:#374151;font-size:12px;margin-top:32px;">
      SchemaZero · schema change detection and impact analysis<br>
      You are receiving this because your org has alerts enabled for {risk_level.upper()} risk events.
    </p>
  </div>
</body>
</html>"""
