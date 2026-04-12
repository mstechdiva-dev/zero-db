from datetime import datetime, timezone
from fastapi import APIRouter

router = APIRouter()


@router.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "ok",
        "service": "schemazero-agent",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
