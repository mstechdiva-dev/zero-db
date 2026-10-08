from datetime import datetime, timezone
from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health", tags=["Health"])
async def health_check(request: Request):
    # 200 either way so the deploy goes through; "degraded" lists setting names to fix.
    missing = getattr(request.app.state, "config_problems", [])
    return {
        "status": "degraded" if missing else "ok",
        "missing": missing,
        "service": "schemazero-agent",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
