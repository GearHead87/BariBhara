"""Tool-call parsing: Gemini 3's thought signature must survive the round trip."""

from openai.types.chat import ChatCompletionMessageToolCall

from app.integrations.llm.client import _parse_tool_call
from app.integrations.llm.types import LLMReply

SIGNATURE = {"google": {"thought_signature": "abc123"}}


def _call(**extra: object) -> ChatCompletionMessageToolCall:
    return ChatCompletionMessageToolCall.model_validate(
        {
            "id": "call_1",
            "type": "function",
            "function": {"name": "get_my_rent_status", "arguments": '{"month": "2026-11"}'},
            **extra,
        }
    )


def test_thought_signature_is_sent_back_with_the_tool_call() -> None:
    parsed = _parse_tool_call(_call(extra_content=SIGNATURE))
    assert parsed.arguments == {"month": "2026-11"}

    message = LLMReply(content="", tool_calls=[parsed]).as_message()
    assert message["tool_calls"][0]["extra_content"] == SIGNATURE


def test_providers_without_extra_content_get_a_plain_tool_call() -> None:
    message = LLMReply(content="", tool_calls=[_parse_tool_call(_call())]).as_message()
    assert "extra_content" not in message["tool_calls"][0]
    assert message["tool_calls"][0]["function"]["name"] == "get_my_rent_status"
