import logging

from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional

from services.anthropic_service import AnthropicService
from services.supabase_service import verify_jwt, get_supabase

logger = logging.getLogger(__name__)

router = APIRouter()

SUPPORTED_AGENTS = {"obi", "sully", "sal"}
HANDOFF_SIGNALS = ["HANDOFF:", "CREATE_TICKET", "CREATE_LEAD"]


class ChatRequest(BaseModel):
    agent: str
    message: str
    history: list[dict] = Field(default_factory=list)


class ChatResponse(BaseModel):
    response: str
    handoff: Optional[str] = None
    agent: str


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    request: Request,
    user=Depends(verify_jwt),
):
    if body.agent not in SUPPORTED_AGENTS:
        raise HTTPException(status_code=400, detail=f"Unknown agent: {body.agent}")

    agent_prompts: dict[str, str] = request.app.state.agent_prompts
    if body.agent not in agent_prompts:
        raise HTTPException(
            status_code=500, detail=f"Agent prompt not loaded: {body.agent}"
        )

    system_prompt = agent_prompts[body.agent]
    service = AnthropicService(system_prompt=system_prompt, agent_name=body.agent)

    response_text = await service.chat(
        message=body.message,
        history=body.history or [],
    )

    handoff: Optional[str] = None
    for signal in HANDOFF_SIGNALS:
        if signal in response_text:
            handoff = signal
            break

    # When Sal flags a qualified lead, persist the full conversation so the
    # admin panel can surface it under /admin/leads.
    if handoff == "CREATE_LEAD" and body.agent == "sal":
        # Strip internal routing tokens before storing so the admin summary is clean
        clean_summary = response_text
        for signal in HANDOFF_SIGNALS:
            clean_summary = clean_summary.replace(signal, "").strip()
        await _store_lead(
            org_id=user.get("org_id"),
            user_email=user.get("email"),
            history=body.history,
            last_message=body.message,
            sal_summary=clean_summary,
        )

    # Strip internal routing tokens from the user-visible response
    visible_response = response_text
    for signal in HANDOFF_SIGNALS:
        visible_response = visible_response.replace(signal, "").strip()

    return ChatResponse(response=visible_response, handoff=handoff, agent=body.agent)


async def _store_lead(
    org_id: Optional[str],
    user_email: Optional[str],
    history: list[dict],
    last_message: str,
    sal_summary: str,
) -> None:
    """Persist a CREATE_LEAD event to the leads table (service-role, bypasses RLS)."""
    try:
        full_conversation = history + [
            {"role": "user", "content": last_message},
            {"role": "assistant", "content": sal_summary},
        ]
        supabase = get_supabase()
        supabase.table("leads").insert(
            {
                "org_id": org_id,
                "user_email": user_email,
                "conversation": full_conversation,
                "sal_summary": sal_summary,
            }
        ).execute()
        logger.info("Lead stored for org_id=%s email=%s", org_id, user_email)
    except Exception as exc:
        # Never let lead storage failure break the chat response
        logger.warning("Failed to store lead for org_id=%s: %s", org_id, exc)
