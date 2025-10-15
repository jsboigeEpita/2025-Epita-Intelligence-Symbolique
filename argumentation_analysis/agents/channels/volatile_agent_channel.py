import sys
from collections.abc import AsyncIterable
from typing import TYPE_CHECKING, Any

if sys.version_info >= (3, 12):
    from typing import override  # pragma: no cover
else:
    from typing_extensions import override  # pragma: no cover

from semantic_kernel.agents.channels.agent_channel import AgentChannel
from semantic_kernel.contents.chat_message_content import ChatMessageContent

if TYPE_CHECKING:
    from semantic_kernel.agents.agent import Agent


class VolatileAgentChannel(AgentChannel):
    """A volatile agent channel that stores history in memory."""

    _history: list[ChatMessageContent]

    def __init__(self, agent: "Agent"):
        self._history = []
        self._agent = agent

    @override
    async def receive(self, history: list["ChatMessageContent"]) -> None:
        """Receives a history of messages."""
        self._history.extend(history)

    @override
    async def invoke(
        self, agent: "Agent", **kwargs: Any
    ) -> AsyncIterable[tuple[bool, "ChatMessageContent"]]:
        """Invokes the agent."""
        messages = await agent.invoke(self._history)
        for message in messages:
            yield True, message

    @override
    async def get_history(self) -> AsyncIterable["ChatMessageContent"]:
        """Gets the history of messages."""
        for message in self._history:
            yield message

    @override
    async def reset(self) -> None:
        """Resets the history."""
        self._history = []

    @override
    async def invoke_stream(
        self, agent: "Agent", messages: list[ChatMessageContent], **kwargs: Any
    ) -> AsyncIterable["ChatMessageContent"]:
        """Invoke the agent stream."""
        async for message in agent.invoke_stream(messages, **kwargs):
            yield message
