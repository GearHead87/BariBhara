"""Chat endpoint with a scripted fake LLM (no network): history, prompt, errors."""

from collections.abc import AsyncIterator

import pytest
from httpx import AsyncClient

from app.integrations.llm.dependencies import get_llm_client
from app.integrations.llm.types import LLMReply, LLMUnavailableError, Message, ToolDefinition
from tests.conftest import MakeUser


class FakeLLM:
    def __init__(self, replies: list[LLMReply | Exception]) -> None:
        self.replies = list(replies)
        self.calls: list[tuple[list[Message], list[ToolDefinition] | None]] = []

    async def complete(
        self, messages: list[Message], tools: list[ToolDefinition] | None = None
    ) -> LLMReply:
        self.calls.append(([dict(m) for m in messages], tools))
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


@pytest.fixture
async def fake_llm() -> AsyncIterator[FakeLLM]:
    from app.main import app

    fake = FakeLLM([])
    app.dependency_overrides[get_llm_client] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_llm_client, None)


async def test_chat_sends_history_and_system_prompt(
    client: AsyncClient, make_user: MakeUser, fake_llm: FakeLLM
) -> None:
    user = await make_user("staff", "Md. Karim Uddin")
    fake_llm.replies = [LLMReply(content="Your name is Karim.")]
    res = await client.post(
        "/chat",
        json={
            "message": "What's my name?",
            "history": [
                {"role": "user", "content": "My name is Karim"},
                {"role": "assistant", "content": "Nice to meet you, Karim!"},
            ],
        },
        headers=user.headers,
    )
    assert res.status_code == 200, res.text
    assert res.json() == {"reply": "Your name is Karim.", "tool_calls": [], "sources": []}

    messages, _ = fake_llm.calls[0]
    assert messages[0]["role"] == "system"
    assert "BariBhara assistant" in messages[0]["content"]
    assert "Md. Karim Uddin" in messages[0]["content"]
    assert [m["role"] for m in messages[1:]] == ["user", "assistant", "user"]
    assert messages[-1]["content"] == "What's my name?"


async def test_chat_requires_login(client: AsyncClient) -> None:
    assert (await client.post("/chat", json={"message": "hi"})).status_code == 401


async def test_chat_validates_input(client: AsyncClient, make_user: MakeUser) -> None:
    user = await make_user("tenant")
    res = await client.post("/chat", json={"message": ""}, headers=user.headers)
    assert res.status_code == 422
    history = [{"role": "user", "content": "x"}] * 21
    res = await client.post(
        "/chat", json={"message": "hi", "history": history}, headers=user.headers
    )
    assert res.status_code == 422


async def test_llm_outage_is_503(
    client: AsyncClient, make_user: MakeUser, fake_llm: FakeLLM
) -> None:
    user = await make_user("tenant")
    fake_llm.replies = [LLMUnavailableError()]
    res = await client.post("/chat", json={"message": "hello"}, headers=user.headers)
    assert res.status_code == 503
    assert "temporarily unavailable" in res.json()["detail"]
