from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ConnectedDatabase(BaseModel):
    id: str
    org_id: str
    engine: str
    display_name: str
    is_active: bool
    created_at: datetime


class CreateDatabaseRequest(BaseModel):
    engine: str
    display_name: str
    connection_string: str
