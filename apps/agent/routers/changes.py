from fastapi import APIRouter, Depends, Query

from models.change_event import ChangeEvent, ImpactAnalysis
from services.supabase_service import SupabaseService, verify_jwt

router = APIRouter()


@router.get("/", response_model=list[ChangeEvent])
async def list_changes(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    user=Depends(verify_jwt),
):
    svc = SupabaseService()
    return await svc.get_change_events(
        org_id=user["org_id"], limit=limit, offset=offset
    )


@router.get("/{change_id}", response_model=ChangeEvent)
async def get_change(change_id: str, user=Depends(verify_jwt)):
    svc = SupabaseService()
    return await svc.get_change_event(change_id=change_id, org_id=user["org_id"])


@router.get("/{change_id}/impact", response_model=ImpactAnalysis)
async def get_impact(change_id: str, user=Depends(verify_jwt)):
    svc = SupabaseService()
    return await svc.get_impact_analysis(change_id=change_id, org_id=user["org_id"])
