"""Provider-neutral shapes. The rest of the app never sees the SDK's own objects."""

from dataclasses import dataclass, field
from typing import Any

from app.core.exceptions import ServiceUnavailableError

# An OpenAI-style chat message ({"role": ..., "content": ..., ...}).
Message = dict[str, Any]
# An OpenAI-style tool definition ({"type": "function", "function": {...}}).
ToolDefinition = dict[str, Any]


@dataclass(frozen=True)
class ToolCallRequest:
    id: str
    name: str
    arguments: dict[str, Any] | None  # None when the model sent invalid JSON
    raw_arguments: str
    # Provider-specific fields that must be echoed back on the next turn, e.g. Gemini 3's
    # {"google": {"thought_signature": ...}}; without it Gemini rejects the follow-up call.
    extra_content: dict[str, Any] | None = None


@dataclass(frozen=True)
class LLMReply:
    content: str
    tool_calls: list[ToolCallRequest] = field(default_factory=list)

    def as_message(self) -> Message:
        """The assistant turn to append to the conversation before sending tool results."""
        message: Message = {"role": "assistant", "content": self.content or None}
        if self.tool_calls:
            message["tool_calls"] = [_tool_call_message(call) for call in self.tool_calls]
        return message


def _tool_call_message(call: ToolCallRequest) -> dict[str, Any]:
    message: dict[str, Any] = {
        "id": call.id,
        "type": "function",
        "function": {"name": call.name, "arguments": call.raw_arguments},
    }
    if call.extra_content:
        message["extra_content"] = call.extra_content
    return message


class LLMUnavailableError(ServiceUnavailableError):
    code = "llm_unavailable"
    default_message = "The assistant is temporarily unavailable. Please try again in a minute."
