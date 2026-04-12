"""Internal router — endpoints called by Scout and other backend services.

These endpoints are NOT authenticated via Supabase JWT. They are intended for
internal service-to-service calls only (Scout → Zero). They should be
protected at the infrastructure level (Railway private networking or a
shared secret header) and never exposed publicly.
"""

import logging
import os

from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)

INTERNAL_SECRET = os.environ.get("INTERNAL_API_SECRET", "")


def _verify_internal(x_internal_secret: str = Header(default="")) -> None:
    if INTERNAL_SECRET and x_internal_secret != INTERNAL_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")


class AnalyzeRequest(BaseModel):
    change_event_id: str


@router.post("/analyze")
async def analyze(
    body: AnalyzeRequest,
    request: Request,
    x_internal_secret: str = Header(default=""),
):
    _verify_internal(x_internal_secret)

    from zero.zero_runner import ZeroRunner

    agent_prompts: dict[str, str] = request.app.state.agent_prompts
    runner = ZeroRunner(agent_prompts=agent_prompts)

    try:
        result = await runner.analyze(change_event_id=body.change_event_id)
        return result
    except Exception as exc:
        logger.error("Zero analysis error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
