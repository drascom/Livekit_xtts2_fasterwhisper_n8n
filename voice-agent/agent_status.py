from __future__ import annotations

import asyncio
import time
from typing import TypedDict


class ModelStatus(TypedDict):
    state: str
    message: str
    updated_at: float


_READY_EVENT = asyncio.Event()

_MODEL_STATUS: dict[str, ModelStatus] = {
    "stt": {
        "state": "pending",
        "message": "Waiting for STT model",
        "updated_at": time.time(),
    },
    "tts": {
        "state": "pending",
        "message": "Waiting for XTTS service",
        "updated_at": time.time(),
    },
    "llm": {
        "state": "pending",
        "message": "Waiting for LLM",
        "updated_at": time.time(),
    },
}


def _refresh_ready_event() -> None:
    if all(entry["state"] == "ready" for entry in _MODEL_STATUS.values()):
        _READY_EVENT.set()


def update_model_status(key: str, state: str, message: str | None = None) -> None:
    if key not in _MODEL_STATUS:
        return

    entry = _MODEL_STATUS[key]
    entry["state"] = state
    entry["message"] = message or entry["message"]
    entry["updated_at"] = time.time()
    _refresh_ready_event()


def get_status_snapshot() -> dict:
    copied = {key: value.copy() for key, value in _MODEL_STATUS.items()}
    ready = all(info["state"] == "ready" for info in copied.values())
    not_ready = next(
        (info["message"] for info in copied.values() if info["state"] != "ready"),
        None,
    )

    return {
        "ready": ready,
        "message": None if ready else not_ready,
        "models": copied,
        "timestamp": time.time(),
    }


async def wait_until_ready(timeout: float | None = None) -> bool:
    if all(info["state"] == "ready" for info in _MODEL_STATUS.values()):
        return True

    try:
        await asyncio.wait_for(_READY_EVENT.wait(), timeout)
        return True
    except asyncio.TimeoutError:
        return False
