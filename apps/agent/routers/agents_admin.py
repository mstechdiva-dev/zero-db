"""Admin router — read and write agent skill MD files.

Endpoints:
  GET  /admin/agents               — list all agents with metadata
  GET  /admin/agents/{name}        — get content + version history
  PUT  /admin/agents/{name}        — save new content (writes disk + Supabase version)
  POST /admin/agents/{name}/revert/{version_id} — revert to a stored version

Auth: all endpoints require the X-Admin-Secret header matching the
ADMIN_SECRET environment variable.  This router is intended to be called
only from the Next.js admin API routes, never directly from the browser.
"""

import logging
import os
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from services.supabase_service import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter()

# Agents directory is two levels up from apps/agent/
AGENTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "agents")
)

ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "")


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------

def verify_admin(x_admin_secret: str = Header(default="")) -> None:
    if not ADMIN_SECRET:
        raise HTTPException(status_code=500, detail="ADMIN_SECRET is not configured")
    if x_admin_secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_path(name: str) -> str:
    """Return the absolute path to an agent MD file, rejecting path traversal."""
    safe = re.sub(r"[^a-zA-Z0-9_-]", "", name)
    if safe != name:
        raise HTTPException(status_code=400, detail="Invalid agent name")
    return os.path.join(AGENTS_DIR, f"{safe}.md")


def _parse_settings(content: str) -> dict:
    settings: dict = {"model": None, "temperature": None, "max_tokens": None}
    m = re.search(r"## Settings\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
    if not m:
        return settings
    text = m.group(1)
    model_m = re.search(r"Model:\s*(.+)", text)
    temp_m = re.search(r"Temperature:\s*(.+)", text)
    tokens_m = re.search(r"Max tokens:\s*(.+)", text)
    if model_m:
        settings["model"] = model_m.group(1).strip()
    if temp_m:
        try:
            settings["temperature"] = float(temp_m.group(1).strip())
        except ValueError:
            pass
    if tokens_m:
        try:
            settings["max_tokens"] = int(tokens_m.group(1).strip())
        except ValueError:
            pass
    return settings


def _parse_role(content: str) -> str:
    m = re.search(r"## Role\s*\n\s*\n(.+)", content)
    return m.group(1).strip() if m else ""


def _load_versions(name: str) -> list:
    try:
        supa = get_supabase()
        result = (
            supa.table("agent_skill_versions")
            .select("id, saved_by, saved_at, label")
            .eq("agent_name", name)
            .order("saved_at", desc=True)
            .limit(20)
            .execute()
        )
        return result.data or []
    except Exception as exc:
        logger.warning("Could not load version history for %s: %s", name, exc)
        return []


def _save_version(name: str, content: str, saved_by: Optional[str], label: Optional[str]) -> None:
    try:
        supa = get_supabase()
        supa.table("agent_skill_versions").insert(
            {
                "agent_name": name,
                "content": content,
                "saved_by": saved_by,
                "label": label,
                "saved_at": datetime.now(tz=timezone.utc).isoformat(),
            }
        ).execute()
    except Exception as exc:
        logger.warning("Could not save version for %s: %s", name, exc)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/admin/agents")
async def list_agents(_: None = Depends(verify_admin)):
    """Return all agent MD files with parsed metadata."""
    if not os.path.isdir(AGENTS_DIR):
        return {"agents": []}

    agents = []
    for filename in sorted(os.listdir(AGENTS_DIR)):
        if not filename.endswith(".md"):
            continue
        name = filename[:-3]
        filepath = os.path.join(AGENTS_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        mtime = os.path.getmtime(filepath)
        agents.append(
            {
                "name": name,
                "role": _parse_role(content),
                "settings": _parse_settings(content),
                "last_modified": datetime.fromtimestamp(
                    mtime, tz=timezone.utc
                ).isoformat(),
                "size_bytes": len(content.encode("utf-8")),
            }
        )
    return {"agents": agents}


@router.get("/admin/agents/{name}")
async def get_agent(name: str, _: None = Depends(verify_admin)):
    """Return the full content and version history for one agent."""
    filepath = _safe_path(name)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"Agent '{name}' not found")

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    return {
        "name": name,
        "content": content,
        "role": _parse_role(content),
        "settings": _parse_settings(content),
        "versions": _load_versions(name),
    }


class SaveRequest(BaseModel):
    content: str
    saved_by: Optional[str] = None
    label: Optional[str] = None


@router.put("/admin/agents/{name}")
async def save_agent(name: str, body: SaveRequest, _: None = Depends(verify_admin)):
    """Write new content to disk and record a version snapshot."""
    filepath = _safe_path(name)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"Agent '{name}' not found")

    if not body.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty")

    _save_version(name, body.content, body.saved_by, body.label)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(body.content)

    return {
        "name": name,
        "saved": True,
        "settings": _parse_settings(body.content),
        "versions": _load_versions(name),
    }


@router.post("/admin/agents/{name}/revert/{version_id}")
async def revert_agent(
    name: str,
    version_id: str,
    saved_by: Optional[str] = None,
    _: None = Depends(verify_admin),
):
    """Revert agent to a stored version (saves the revert as a new version)."""
    filepath = _safe_path(name)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"Agent '{name}' not found")

    try:
        supa = get_supabase()
        result = (
            supa.table("agent_skill_versions")
            .select("content, saved_at")
            .eq("id", version_id)
            .eq("agent_name", name)
            .single()
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    if not result.data:
        raise HTTPException(status_code=404, detail="Version not found")

    old_content = result.data["content"]
    old_date = result.data["saved_at"][:10]

    _save_version(name, old_content, saved_by, f"Reverted to {old_date}")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(old_content)

    return {
        "name": name,
        "content": old_content,
        "reverted": True,
        "versions": _load_versions(name),
    }
