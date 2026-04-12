from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from services.anthropic_service import AnthropicService
from services.supabase_service import verify_jwt

router = APIRouter()

SUPPORTED_AGENTS = {"shawn", "taylor", "jordan"}
HANDOFF_SIGNALS = ["HANDOFF:", "CREATE_TICKET", "CREATE_LEAD"]


class ChatRequest(BaseModel):
    agent: str
    message: str
    history: Optional[list[dict]] = []


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

    return ChatResponse(response=response_text, handoff=handoff, agent=body.agent)
