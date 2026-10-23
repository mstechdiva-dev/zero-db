from fastapi import APIRouter, Depends, HTTPException

from models.database import ConnectedDatabase, CreateDatabaseRequest
from services.supabase_service import SupabaseService, get_supabase, verify_jwt
from services.encryption_service import EncryptionService
from services.entitlement import db_limit, db_limit_message, require_access
from services.connection_test import ConnectionTestError, test_connection
from scout.listeners.postgres_listener import remove_ddl_trigger

POSTGRES_ENGINES = {"postgresql", "supabase", "neon", "cockroachdb"}

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

    # Expired trial and not paying: no new databases until they upgrade.
    # Over the plan's connection limit: same. Can't check the plan: no.
    org = require_access(get_supabase(), user["org_id"])
    limit = db_limit(org)
    if limit is not None:
        existing = await SupabaseService().get_connected_databases(org_id=user["org_id"])
        if len(existing) >= limit:
            raise HTTPException(status_code=403, detail=db_limit_message(limit))

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
    # Take our trigger back out of their database first (best effort), while
    # we still hold the connection string.
    row = (
        svc.client.table("connected_databases")
        .select("engine, encrypted_connection_string")
        .eq("id", database_id)
        .eq("org_id", user["org_id"])
        .execute()
        .data
    )
    if row and row[0]["engine"] in POSTGRES_ENGINES:
        try:
            conn_string = EncryptionService().decrypt(row[0]["encrypted_connection_string"])
            await remove_ddl_trigger(conn_string)
        except Exception:
            pass  # never block the delete on cleanup
    await svc.delete_connected_database(
        database_id=database_id, org_id=user["org_id"]
    )
