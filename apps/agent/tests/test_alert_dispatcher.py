"""Unit tests for apps/agent/zero/alert_dispatcher.py

Tests alert routing logic:
- Webhook is always fired first when configured
- Slack fires for HIGH and CRITICAL only
- PagerDuty fires for CRITICAL only
- Email fires based on org email_recipients config
- Failures in one channel do not prevent subsequent channels
- Channels are skipped when risk_level is not in notify_on
- notification_log entry is written for every channel attempt
"""

import sys
import os
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from zero.alert_dispatcher import AlertDispatcher


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_dispatcher(alert_config: dict, database_name: str = "prod-db"):
    """Return an AlertDispatcher with a mocked Supabase client."""
    mock_supa = MagicMock()

    # _get_alert_config
    alert_config_result = MagicMock()
    alert_config_result.data = alert_config

    # _get_database_name
    db_result = MagicMock()
    db_result.data = {"display_name": database_name}

    # notification_log insert
    insert_chain = MagicMock()
    mock_supa.table.return_value.insert.return_value.execute = MagicMock(return_value=None)
    mock_supa.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute = MagicMock(return_value=db_result)
    mock_supa.table.return_value.select.return_value.eq.return_value.single.return_value.execute = MagicMock(return_value=alert_config_result)

    return AlertDispatcher(mock_supa)


def _change_event(risk_level="high"):
    return {
        "id": "evt-001",
        "database_id": "db-001",
        "engine": "postgresql",
        "change_type": "column_dropped",
        "object_type": "column",
        "object_name": "email",
        "risk_level": risk_level,
    }


def _impact():
    return {
        "summary": "The email column was dropped from the users table.",
        "next_action": "Do not deploy until this is resolved.",
    }


# ---------------------------------------------------------------------------
# Channel skipping when risk not in notify_on
# ---------------------------------------------------------------------------

class TestNotifyOnFiltering:
    @pytest.mark.asyncio
    async def test_no_alerts_when_risk_not_in_notify_on(self):
        config = {"notify_on": ["high", "critical"]}
        dispatcher = _make_dispatcher(config)

        with patch.object(dispatcher, "_fire_webhook", new_callable=AsyncMock) as mock_wh, \
             patch.object(dispatcher, "_fire_slack", new_callable=AsyncMock) as mock_sl, \
             patch.object(dispatcher, "_fire_pagerduty", new_callable=AsyncMock) as mock_pd, \
             patch.object(dispatcher, "_fire_email", new_callable=AsyncMock) as mock_em, \
             patch.object(dispatcher, "_get_alert_config", new_callable=AsyncMock, return_value=config), \
             patch.object(dispatcher, "_get_database_name", new_callable=AsyncMock, return_value="prod-db"):

            await dispatcher.dispatch("org-1", _change_event("low"), _impact(), "low")

        mock_wh.assert_not_called()
        mock_sl.assert_not_called()
        mock_pd.assert_not_called()
        mock_em.assert_not_called()

    @pytest.mark.asyncio
    async def test_alerts_fire_when_risk_matches(self):
        config = {
            "notify_on": ["high", "critical"],
            "webhook_url": "https://hooks.example.com/test",
        }
        dispatcher = _make_dispatcher(config)

        with patch.object(dispatcher, "_fire_webhook", new_callable=AsyncMock) as mock_wh, \
             patch.object(dispatcher, "_fire_slack", new_callable=AsyncMock) as mock_sl, \
             patch.object(dispatcher, "_get_alert_config", new_callable=AsyncMock, return_value=config), \
             patch.object(dispatcher, "_get_database_name", new_callable=AsyncMock, return_value="prod-db"):

            await dispatcher.dispatch("org-1", _change_event("high"), _impact(), "high")

        mock_wh.assert_called_once()
        mock_sl.assert_called_once()


# ---------------------------------------------------------------------------
# Webhook — always first
# ---------------------------------------------------------------------------

class TestWebhookChannel:
    @pytest.mark.asyncio
    async def test_webhook_fires_when_configured(self):
        config = {
            "notify_on": ["high", "critical"],
            "webhook_url": "https://hooks.example.com/test",
        }
        dispatcher = _make_dispatcher(config)

        with patch.object(dispatcher, "_fire_webhook", new_callable=AsyncMock) as mock_wh, \
             patch.object(dispatcher, "_fire_slack", new_callable=AsyncMock), \
             patch.object(dispatcher, "_get_alert_config", new_callable=AsyncMock, return_value=config), \
             patch.object(dispatcher, "_get_database_name", new_callable=AsyncMock, return_value="prod-db"):

            await dispatcher.dispatch("org-1", _change_event("high"), _impact(), "high")

        mock_wh.assert_called_once()

    @pytest.mark.asyncio
    async def test_webhook_fires_even_without_url(self):
        """Webhook method is always called; the service handles missing URL gracefully."""
        config = {
            "notify_on": ["high", "critical"],
        }
        dispatcher = _make_dispatcher(config)

        with patch.object(dispatcher, "_fire_webhook", new_callable=AsyncMock) as mock_wh, \
             patch.object(dispatcher, "_fire_slack", new_callable=AsyncMock), \
             patch.object(dispatcher, "_get_alert_config", new_callable=AsyncMock, return_value=config), \
             patch.object(dispatcher, "_get_database_name", new_callable=AsyncMock, return_value="prod-db"):

            await dispatcher.dispatch("org-1", _change_event("high"), _impact(), "high")

        mock_wh.assert_called_once()


# ---------------------------------------------------------------------------
# Slack — HIGH and CRITICAL only
# ---------------------------------------------------------------------------

class TestSlackChannel:
    @pytest.mark.asyncio
    async def test_slack_fires_for_high(self):
        config = {"notify_on": ["high", "critical"]}
        dispatcher = _make_dispatcher(config)

        with patch.object(dispatcher, "_fire_webhook", new_callable=AsyncMock), \
             patch.object(dispatcher, "_fire_slack", new_callable=AsyncMock) as mock_sl, \
             patch.object(dispatcher, "_get_alert_config", new_callable=AsyncMock, return_value=config), \
             patch.object(dispatcher, "_get_database_name", new_callable=AsyncMock, return_value="prod-db"):

            await dispatcher.dispatch("org-1", _change_event("high"), _impact(), "high")

        mock_sl.assert_called_once()

    @pytest.mark.asyncio
    async def test_slack_fires_for_critical(self):
        config = {"notify_on": ["critical"]}
        dispatcher = _make_dispatcher(config)

        with patch.object(dispatcher, "_fire_webhook", new_callable=AsyncMock), \
             patch.object(dispatcher, "_fire_slack", new_callable=AsyncMock) as mock_sl, \
             patch.object(dispatcher, "_fire_pagerduty", new_callable=AsyncMock), \
             patch.object(dispatcher, "_get_alert_config", new_callable=AsyncMock, return_value=config), \
             patch.object(dispatcher, "_get_database_name", new_callable=AsyncMock, return_value="prod-db"):

            await dispatcher.dispatch("org-1", _change_event("critical"), _impact(), "critical")

        mock_sl.assert_called_once()

    @pytest.mark.asyncio
    async def test_slack_does_not_fire_for_medium(self):
        config = {"notify_on": ["low", "medium", "high", "critical"]}
        dispatcher = _make_dispatcher(config)

        with patch.object(dispatcher, "_fire_webhook", new_callable=AsyncMock), \
             patch.object(dispatcher, "_fire_slack", new_callable=AsyncMock) as mock_sl, \
             patch.object(dispatcher, "_get_alert_config", new_callable=AsyncMock, return_value=config), \
             patch.object(dispatcher, "_get_database_name", new_callable=AsyncMock, return_value="prod-db"):

            await dispatcher.dispatch("org-1", _change_event("medium"), _impact(), "medium")

        mock_sl.assert_not_called()

    @pytest.mark.asyncio
    async def test_slack_does_not_fire_for_low(self):
        config = {"notify_on": ["low", "medium", "high", "critical"]}
        dispatcher = _make_dispatcher(config)

        with patch.object(dispatcher, "_fire_webhook", new_callable=AsyncMock), \
             patch.object(dispatcher, "_fire_slack", new_callable=AsyncMock) as mock_sl, \
             patch.object(dispatcher, "_get_alert_config", new_callable=AsyncMock, return_value=config), \
             patch.object(dispatcher, "_get_database_name", new_callable=AsyncMock, return_value="prod-db"):

            await dispatcher.dispatch("org-1", _change_event("low"), _impact(), "low")

        mock_sl.assert_not_called()


# ---------------------------------------------------------------------------
# PagerDuty — CRITICAL only
# ---------------------------------------------------------------------------

class TestPagerDutyChannel:
    @pytest.mark.asyncio
    async def test_pagerduty_fires_for_critical(self):
        config = {"notify_on": ["critical"]}
        dispatcher = _make_dispatcher(config)

        with patch.object(dispatcher, "_fire_webhook", new_callable=AsyncMock), \
             patch.object(dispatcher, "_fire_slack", new_callable=AsyncMock), \
             patch.object(dispatcher, "_fire_pagerduty", new_callable=AsyncMock) as mock_pd, \
             patch.object(dispatcher, "_get_alert_config", new_callable=AsyncMock, return_value=config), \
             patch.object(dispatcher, "_get_database_name", new_callable=AsyncMock, return_value="prod-db"):

            await dispatcher.dispatch("org-1", _change_event("critical"), _impact(), "critical")

        mock_pd.assert_called_once()

    @pytest.mark.asyncio
    async def test_pagerduty_does_not_fire_for_high(self):
        config = {"notify_on": ["high", "critical"]}
        dispatcher = _make_dispatcher(config)

        with patch.object(dispatcher, "_fire_webhook", new_callable=AsyncMock), \
             patch.object(dispatcher, "_fire_slack", new_callable=AsyncMock), \
             patch.object(dispatcher, "_fire_pagerduty", new_callable=AsyncMock) as mock_pd, \
             patch.object(dispatcher, "_get_alert_config", new_callable=AsyncMock, return_value=config), \
             patch.object(dispatcher, "_get_database_name", new_callable=AsyncMock, return_value="prod-db"):

            await dispatcher.dispatch("org-1", _change_event("high"), _impact(), "high")

        mock_pd.assert_not_called()


# ---------------------------------------------------------------------------
# Email — based on email_recipients config
# ---------------------------------------------------------------------------

class TestEmailChannel:
    @pytest.mark.asyncio
    async def test_email_fires_when_recipients_configured(self):
        config = {
            "notify_on": ["high", "critical"],
            "email_recipients": ["team@example.com"],
        }
        dispatcher = _make_dispatcher(config)

        with patch.object(dispatcher, "_fire_webhook", new_callable=AsyncMock), \
             patch.object(dispatcher, "_fire_slack", new_callable=AsyncMock), \
             patch.object(dispatcher, "_fire_email", new_callable=AsyncMock) as mock_em, \
             patch.object(dispatcher, "_get_alert_config", new_callable=AsyncMock, return_value=config), \
             patch.object(dispatcher, "_get_database_name", new_callable=AsyncMock, return_value="prod-db"):

            await dispatcher.dispatch("org-1", _change_event("high"), _impact(), "high")

        mock_em.assert_called_once()

    @pytest.mark.asyncio
    async def test_email_does_not_fire_when_no_recipients(self):
        config = {
            "notify_on": ["high", "critical"],
            "email_recipients": [],
        }
        dispatcher = _make_dispatcher(config)

        with patch.object(dispatcher, "_fire_webhook", new_callable=AsyncMock), \
             patch.object(dispatcher, "_fire_slack", new_callable=AsyncMock), \
             patch.object(dispatcher, "_fire_email", new_callable=AsyncMock) as mock_em, \
             patch.object(dispatcher, "_get_alert_config", new_callable=AsyncMock, return_value=config), \
             patch.object(dispatcher, "_get_database_name", new_callable=AsyncMock, return_value="prod-db"):

            await dispatcher.dispatch("org-1", _change_event("high"), _impact(), "high")

        mock_em.assert_not_called()


# ---------------------------------------------------------------------------
# Fault isolation — channel failure does not prevent others
# ---------------------------------------------------------------------------

class TestFaultIsolation:
    @pytest.mark.asyncio
    async def test_slack_failure_does_not_prevent_pagerduty(self):
        config = {
            "notify_on": ["critical"],
            "email_recipients": [],
        }
        dispatcher = _make_dispatcher(config)

        async def failing_slack(**kwargs):
            raise RuntimeError("Slack is down")

        with patch.object(dispatcher, "_fire_webhook", new_callable=AsyncMock), \
             patch.object(dispatcher, "_fire_slack", side_effect=failing_slack), \
             patch.object(dispatcher, "_fire_pagerduty", new_callable=AsyncMock) as mock_pd, \
             patch.object(dispatcher, "_get_alert_config", new_callable=AsyncMock, return_value=config), \
             patch.object(dispatcher, "_get_database_name", new_callable=AsyncMock, return_value="prod-db"):

            # Should not raise
            await dispatcher.dispatch("org-1", _change_event("critical"), _impact(), "critical")

        mock_pd.assert_called_once()
