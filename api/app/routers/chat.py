"""Chat endpoint for conversational AI."""

from fastapi import APIRouter
from pydantic import BaseModel

from api.app.services.chat import chat
from data.scripts.db.session import get_session_factory

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


class ChatResponse(BaseModel):
    response: str
    tools_used: list[str]


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    """Send a natural language question and get a data-grounded answer."""
    session_factory = get_session_factory()
    with session_factory() as session:
        result = chat(req.message, req.history, session)
    return ChatResponse(**result)
