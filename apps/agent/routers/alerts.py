from fastapi import APIRouter, Depends

from models.alert import AlertConfig, UpdateAlertConfigRequest
from services.supabase_service import SupabaseService, verify_jwt

router = APIRouter()


@router.get("/config", response_model=AlertConfig)
async def get_alert_config(user=Depends(verify_jwt)):
    svc = SupabaseService()
    return await svc.get_alert_config(org_id=user["org_id"])


@router.put("/config", response_model=AlertConfig)
async def update_alert_config(
    body: UpdateAlertConfigRequest, user=Depends(verify_jwt)
):
    svc = SupabaseService()
    return await svc.update_alert_config(org_id=user["org_id"], config=body)
