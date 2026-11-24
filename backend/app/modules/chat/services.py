from datetime import date

from app.integrations.llm.client import LLMClient
from app.integrations.llm.types import Message
from app.modules.chat.prompts import AskerContext, build_system_prompt
from app.modules.chat.schemas import MAX_HISTORY, ChatRequest, ChatResponse
from app.modules.leases.repositories import LeaseRepository
from app.modules.users.models import RoleName, User


class ChatService:
    def __init__(self, llm: LLMClient, leases: LeaseRepository) -> None:
        self.llm = llm
        self.leases = leases

    async def chat(self, user: User, request: ChatRequest) -> ChatResponse:
        system_prompt = build_system_prompt(await self._asker(user), [], date.today())
        messages: list[Message] = [{"role": "system", "content": system_prompt}]
        messages += [turn.model_dump() for turn in request.history[-MAX_HISTORY:]]
        messages.append({"role": "user", "content": request.message})

        reply = await self.llm.complete(messages)
        return ChatResponse(reply=reply.content)

    async def _asker(self, user: User) -> AskerContext:
        context = AskerContext(name=user.full_name, role=user.role_name)
        if user.role_name == RoleName.TENANT:
            lease = await self.leases.active_for_tenant(user.id)
            if lease is not None:
                context = AskerContext(
                    name=user.full_name,
                    role=user.role_name,
                    building=lease.flat.building.name,
                    flat_no=lease.flat.flat_no,
                    area=lease.flat.building.area,
                )
        return context
