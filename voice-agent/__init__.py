"""
Voice Agent
===========

A modular voice assistant with n8n workflow integrations and local LLM support.

Core Components:
    OllamaLLM: Native Ollama LLM with think parameter support for Qwen3

STT/TTS:
    - Speaches container for Faster-Whisper STT
    - Kokoro container for TTS

Integrations:
    n8n: Workflow discovery and execution via n8n MCP

Example:
    >>> from llm.ollama_llm import OllamaLLM
    >>> from integrations import load_mcp_config
    >>>
    >>> llm = OllamaLLM(model="qwen3:8b", think=False)
    >>> mcp_configs = load_mcp_config()

Repository: local
"""

__version__ = "0.1.0"
__author__ = "CoreWorxLab"

from .llm import OllamaLLM

__all__ = [
    "OllamaLLM",
    "__version__",
]
