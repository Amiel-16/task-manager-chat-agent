from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.agent.graph import run_agent
from app.core.config import settings
from app.schemas.chat import ChatRequest, ChatResponse


app = FastAPI(title=settings.app_name)
security = HTTPBearer()

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> ChatResponse:
    try:
        token = credentials.credentials
        response = await run_agent(request.message, token=token, thread_id=request.thread_id)
        return ChatResponse(response=response)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {exc}") from exc
