from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User message for the chat agent")
    thread_id: str | None = Field(
        default=None,
        description="Stable id for this conversation so checkpoint memory can persist across requests",
    )


class ChatResponse(BaseModel):
    response: str
