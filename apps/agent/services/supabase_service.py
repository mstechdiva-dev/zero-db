import os
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import create_client, Client

security = HTTPBearer()


def get_supabase() -> Client:
    url = os.environ["NEXT_PUBLIC_SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    return create_client(url, key)


async def verify_jwt(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> dict:
    supabase = get_supabase()
    try:
        result = supabase.auth.get_user(credentials.credentials)
        if not result or not result.user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        user_result = (
            supabase.table("users")
            .select("org_id, role")
            .eq("auth_user_id", result.user.id)
            .single()
            .execute()
        )
        if not user_result.data or not user_result.data.get("org_id"):
            raise HTTPException(
                status_code=403, detail="User is not assigned to an organization"
            )

        return {
            "user_id": result.user.id,
            "email": result.user.email,
            "org_id": user_result.data["org_id"],
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Authentication failed")


class SupabaseService:
    def __init__(self):
        self.client = get_supabase()

    async def get_connected_databases(self, org_id: str) -> list[dict]:
        result = (
            self.client.table("connected_databases")
            .select("id, org_id, engine, display_name, is_active, created_at")
            .eq("org_id", org_id)
            .execute()
        )
        return result.data or []

    async def create_connected_database(
        self,
        org_id: str,
        engine: str,
        display_name: str,
        encrypted_connection_string: str,
    ) -> dict:
        result = (
            self.client.table("connected_databases")
            .insert(
                {
                    "org_id": org_id,
                    "engine": engine,
                    "display_name": display_name,
                    "encrypted_connection_string": encrypted_connection_string,
                    "is_active": True,
                }
            )
            .execute()
        )
        if getattr(result, "error", None):
            raise HTTPException(
                status_code=400,
                detail=f"Failed to create connected database: {result.error}",
            )
        if not result.data:
            raise HTTPException(status_code=502, detail="Failed to create connected database")
        return result.data[0]

    async def delete_connected_database(self, database_id: str, org_id: str):
        self.client.table("connected_databases").delete().eq(
            "id", database_id
        ).eq("org_id", org_id).execute()

    async def get_change_events(
        self, org_id: str, limit: int = 50, offset: int = 0
    ) -> list[dict]:
        result = (
            self.client.table("change_events")
            .select("*")
            .eq("org_id", org_id)
            .order("detected_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return result.data or []

    async def get_change_event(self, change_id: str, org_id: str) -> dict:
        result = (
            self.client.table("change_events")
            .select("*")
            .eq("id", change_id)
            .eq("org_id", org_id)
            .single()
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Change event not found")
        return result.data

    async def get_impact_analysis(self, change_id: str, org_id: str) -> dict:
        # Verify the change event belongs to this org before returning impact
        await self.get_change_event(change_id=change_id, org_id=org_id)
        result = (
            self.client.table("impact_analysis")
            .select("*")
            .eq("change_event_id", change_id)
            .single()
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Impact analysis not found")
        return result.data

    async def get_alert_config(self, org_id: str) -> dict:
        result = (
            self.client.table("alert_configs")
            .select("*")
            .eq("org_id", org_id)
            .single()
            .execute()
        )
        return result.data or {}

    async def update_alert_config(self, org_id: str, config) -> dict:
        result = (
            self.client.table("alert_configs")
            .upsert({"org_id": org_id, **config.model_dump(exclude_unset=True)})
            .execute()
        )
        if getattr(result, "error", None):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update alert config: {result.error}",
            )
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to update alert config")
        return result.data[0]
