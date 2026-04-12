import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import agent, databases, changes, alerts, health

AGENTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "agents")
)


def load_agent_prompts() -> dict[str, str]:
    """Load all agent MD files into memory at startup."""
    prompts: dict[str, str] = {}
    if not os.path.isdir(AGENTS_DIR):
        return prompts
    for filename in os.listdir(AGENTS_DIR):
        if filename.endswith(".md"):
            name = filename[:-3]
            filepath = os.path.join(AGENTS_DIR, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                prompts[name] = f.read()
    return prompts


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: load agent prompts
    app.state.agent_prompts = load_agent_prompts()

    # Scout background task is started in Phase 3/8
    # from scout.scout_runner import ScoutRunner
    # app.state.scout = ScoutRunner()
    # asyncio.create_task(app.state.scout.run())

    yield

    # Shutdown: nothing to clean up in Phase 1


app = FastAPI(
    title="SchemaZero Agent API",
    description="FastAPI backend powering Scout, Zero, and customer-facing agents.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("FRONTEND_URL", "https://schemazero.com"),
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(agent.router, prefix="/agent", tags=["Agent"])
app.include_router(databases.router, prefix="/databases", tags=["Databases"])
app.include_router(changes.router, prefix="/changes", tags=["Changes"])
app.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
