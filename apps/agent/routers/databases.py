from fastapi import APIRouter, Depends, HTTPException

from models.database import ConnectedDatabase, CreateDatabaseRequest
from services.supabase_service import SupabaseService, verify_jwt
from services.encryption_service import EncryptionService

router = APIRouter()


@router.get("/", response_model=list[ConnectedDatabase])
async def list_databases(user=Depends(verify_jwt)):
    svc = SupabaseService()
    return await svc.get_connected_databases(org_id=user["org_id"])


@router.post("/", response_model=ConnectedDatabase, status_code=201)
async def add_database(body: CreateDatabaseRequest, user=Depends(verify_jwt)):
    enc = EncryptionService()
    encrypted_conn = enc.encrypt(body.connection_string)

    svc = SupabaseService()
    return await svc.create_connected_database(
        org_id=user["org_id"],
        engine=body.engine,
        display_name=body.display_name,
        encrypted_connection_string=encrypted_conn,
    )


@router.delete("/{database_id}", status_code=204)
async def remove_database(database_id: str, user=Depends(verify_jwt)):
    svc = SupabaseService()
    await svc.delete_connected_database(
        database_id=database_id, org_id=user["org_id"]
    )
