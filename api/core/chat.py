from fastapi import APIRouter
from pydantic import BaseModel

from .config import settings
from .agent import call_graph


router = APIRouter()


class MessagePayload(BaseModel):
    message: str


@router.post(path="/message")
async def message(payload: MessagePayload):
    result = call_graph(payload.message)
    return {"result": result}

