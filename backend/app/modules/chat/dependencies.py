from typing import Annotated

from fastapi import Depends

from app.integrations.llm.client import LLMClient
from app.integrations.llm.dependencies import get_llm_client
from app.modules.chat.services import ChatService
from app.modules.users.dependencies import DbSession


def get_chat_service(
    llm: Annotated[LLMClient, Depends(get_llm_client)], db: DbSession
) -> ChatService:
    return ChatService(llm, db)
