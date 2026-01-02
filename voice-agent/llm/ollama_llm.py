"""
OllamaLLM Plugin for LiveKit Agents
====================================

Native Ollama LLM integration with think parameter support for Qwen3 models.

This plugin provides an LLM interface that satisfies LiveKit's requirements
while allowing the VoiceAssistant's llm_node override to handle actual
LLM calls with MCP tool integration.

Features:
    - Supports Qwen3's think parameter for low-latency responses
    - Configuration accessible via properties for llm_node override
    - Minimal implementation - llm_node does the real work

Example:
    >>> from caal import OllamaLLM
    >>> from livekit.agents import AgentSession
    >>>
    >>> llm = OllamaLLM(
    ...     model="qwen3:8b",
    ...     think=False,  # Disable thinking for lower latency
    ...     temperature=0.7,
    ... )
    >>>
    >>> session = AgentSession(stt=..., llm=llm, tts=...)
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from livekit.agents import llm
from livekit.agents.llm import ChatContext, ChatChunk, ChoiceDelta
from livekit.agents.llm.tool_context import FunctionTool, RawFunctionTool
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS, APIConnectOptions, NOT_GIVEN, NotGivenOr

__all__ = ["OllamaLLM"]

logger = logging.getLogger(__name__)


class OllamaLLM(llm.LLM):
    """
    LiveKit LLM plugin for Ollama with think parameter support.

    This plugin is designed to be used with a VoiceAssistant that overrides
    the llm_node method. The actual LLM calls are handled by ollama_llm_node(),
    which supports MCP tool discovery and execution.

    The OllamaLLM class:
    1. Satisfies LiveKit's llm.LLM interface (prevents "no LLM" errors)
    2. Stores configuration accessible via properties
    3. Provides model/provider info for logging and metrics

    Args:
        model: Ollama model name (e.g., "qwen3:8b", "llama3.2:3b")
        think: Enable Qwen3 thinking mode. False for lower latency.
        temperature: Sampling temperature (0.0-2.0)
        top_p: Nucleus sampling threshold (0.0-1.0)
        top_k: Top-k sampling limit
        base_url: Ollama server URL

    Example:
        >>> llm = OllamaLLM(model="qwen3:8b", think=False)
        >>> session = AgentSession(llm=llm, ...)
    """

    def __init__(
        self,
        *,
        model: str = "qwen3:8b",
        think: bool = False,
        temperature: float = 0.7,
        top_p: float = 0.8,
        top_k: int = 20,
        num_ctx: int = 8192,
        base_url: str = "http://localhost:11434",
    ) -> None:
        super().__init__()
        self._model = model
        self._think = think
        self._temperature = temperature
        self._top_p = top_p
        self._top_k = top_k
        self._num_ctx = num_ctx
        self._base_url = base_url

        logger.debug(f"OllamaLLM initialized: {model} (think={think}, num_ctx={num_ctx})")

    # === Required LLM interface properties ===

    @property
    def model(self) -> str:
        """Model name for logging and metrics."""
        return self._model

    @property
    def provider(self) -> str:
        """Provider name for logging and metrics."""
        return "ollama"

    # === Configuration accessors for llm_node ===

    @property
    def think(self) -> bool:
        """Whether to use Qwen3 thinking mode."""
        return self._think

    @property
    def temperature(self) -> float:
        """Sampling temperature."""
        return self._temperature

    @property
    def top_p(self) -> float:
        """Nucleus sampling threshold."""
        return self._top_p

    @property
    def top_k(self) -> int:
        """Top-k sampling limit."""
        return self._top_k

    @property
    def num_ctx(self) -> int:
        """Context window size."""
        return self._num_ctx

    @property
    def base_url(self) -> str:
        """Ollama server URL."""
        return self._base_url

    # === Required LLM interface method ===

    def chat(
        self,
        *,
        chat_ctx: ChatContext,
        tools: list[FunctionTool | RawFunctionTool] | None = None,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
        parallel_tool_calls: NotGivenOr[bool] = NOT_GIVEN,
        tool_choice: NotGivenOr[llm.ToolChoice] = NOT_GIVEN,
        extra_kwargs: NotGivenOr[dict[str, Any]] = NOT_GIVEN,
    ) -> llm.LLMStream:
        """
        Create an LLM stream for chat completion.

        Note: When using VoiceAssistant with llm_node override, this method
        is bypassed. The llm_node override calls ollama_llm_node() directly.

        This implementation exists for interface compliance and fallback.
        """
        return _OllamaLLMStream(
            llm=self,
            chat_ctx=chat_ctx,
            tools=tools or [],
            conn_options=conn_options,
        )

    async def aclose(self) -> None:
        """Cleanup (no-op for Ollama)."""
        pass


class _OllamaLLMStream(llm.LLMStream):
    """
    Minimal LLMStream implementation for interface compliance.

    In practice, VoiceAssistant's llm_node override bypasses this entirely.
    This exists to satisfy the type system and handle edge cases.
    """

    def __init__(
        self,
        llm: OllamaLLM,
        *,
        chat_ctx: ChatContext,
        tools: list[FunctionTool | RawFunctionTool],
        conn_options: APIConnectOptions,
    ) -> None:
        super().__init__(llm, chat_ctx=chat_ctx, tools=tools, conn_options=conn_options)
        self._ollama_llm = llm

    async def _run(self) -> None:
        """
        Minimal implementation that emits an empty response.

        This method is typically never called because VoiceAssistant's
        llm_node override handles all LLM interactions via ollama_llm_node().

        If this is called unexpectedly, it emits a placeholder response
        to prevent crashes.
        """
        request_id = str(uuid.uuid4())

        # Emit a minimal response for interface compliance
        # In normal operation, llm_node override prevents this from running
        logger.warning(
            "OllamaLLM._run() called directly - this usually means llm_node "
            "override is not active. Using fallback response."
        )

        chunk = ChatChunk(
            id=request_id,
            delta=ChoiceDelta(
                role="assistant",
                content="I'm configured to use a custom LLM node. Please ensure the agent's llm_node override is active.",
            ),
        )
        self._event_ch.send_nowait(chunk)
