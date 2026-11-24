from typing import Annotated

from fastapi import Depends

from app.integrations.llm.client import LLMClient
from app.integrations.llm.dependencies import get_llm_client
from app.modules.chat.services import ChatService
from app.modules.leases.dependencies import get_lease_repository
from app.modules.leases.repositories import LeaseRepository


def get_chat_service(
    llm: Annotated[LLMClient, Depends(get_llm_client)],
    leases: Annotated[LeaseRepository, Depends(get_lease_repository)],
) -> ChatService:
    return ChatService(llm, leases)
