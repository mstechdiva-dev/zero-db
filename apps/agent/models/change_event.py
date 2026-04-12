from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel


class ChangeEvent(BaseModel):
    id: str
    org_id: str
    database_id: str
    change_type: str
    object_type: str
    object_name: str
    schema_name: Optional[str] = None
    before_state: Optional[Any] = None
    after_state: Optional[Any] = None
    risk_level: Optional[str] = None
    detected_at: datetime


class ImpactAnalysis(BaseModel):
    id: str
    change_event_id: str
    affected_queries: list[Any]
    affected_services: list[Any]
    affected_indexes: list[Any]
    summary: str
    recommendations: list[Any]
    created_at: datetime
