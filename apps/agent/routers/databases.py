from fastapi import APIRouter, Depends, HTTPException

from models.database import ConnectedDatabase, CreateDatabaseRequest
from services.supabase_service import SupabaseService, verify_jwt
from services.encryption_service import EncryptionService
from services.connection_test import ConnectionTestError, test_connection

router = APIRouter()


@router.get("/", response_model=list[ConnectedDatabase])
async def list_databases(user=Depends(verify_jwt)):
    svc = SupabaseService()
    return await svc.get_connected_databases(org_id=user["org_id"])


@router.post("/", response_model=ConnectedDatabase, status_code=201)
async def add_database(body: CreateDatabaseRequest, user=Depends(verify_jwt)):
    """Test the connection, then store it encrypted. The connection string is
    never logged and never returned."""
    display_name = body.display_name.strip()
    connection_string = body.connection_string.strip()
    if not display_name or not connection_string:
        raise HTTPException(status_code=400, detail="A name and a connection string are required.")

    try:
        await test_connection(body.engine, connection_string)
    except ConnectionTestError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    enc = EncryptionService()
    encrypted_conn = enc.encrypt(connection_string)

    svc = SupabaseService()
    return await svc.create_connected_database(
        org_id=user["org_id"],
        engine=body.engine,
        display_name=display_name,
        encrypted_connection_string=encrypted_conn,
    )


@router.delete("/{database_id}", status_code=204)
async def remove_database(database_id: str, user=Depends(verify_jwt)):
    svc = SupabaseService()
    await svc.delete_connected_database(
        database_id=database_id, org_id=user["org_id"]
    )
