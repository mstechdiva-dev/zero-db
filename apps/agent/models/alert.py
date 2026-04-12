from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class AlertConfig(BaseModel):
    id: Optional[str] = None
    org_id: str
    slack_webhook_url: Optional[str] = None
    pagerduty_api_key: Optional[str] = None
    email_recipients: list[str] = Field(default_factory=list)
    notify_on: list[str] = Field(default_factory=lambda: ["high", "critical"])
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class UpdateAlertConfigRequest(BaseModel):
    slack_webhook_url: Optional[str] = None
    pagerduty_api_key: Optional[str] = None
    email_recipients: Optional[list[str]] = None
    notify_on: Optional[list[str]] = None
