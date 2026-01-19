from fastapi import APIRouter
from pydantic import BaseModel

from .config import settings
from .agent import call_graph
from scripts.ingest_restaurants_api import query_neo4j, download_to_db


router = APIRouter()


class MessagePayload(BaseModel):
    message: str


@router.post(path="/message")
async def message(payload: MessagePayload):
    result = call_graph(payload.message)
    return {"result": result}

    # result = query_neo4j(payload.message)
    # if result == 'NO_RESULTS':
    #     print("building graph...")
    #     download_to_db('Warszawa', "")
    #     result = query_neo4j(payload.message)
    # return {"result": result}

