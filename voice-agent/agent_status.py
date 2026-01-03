from __future__ import annotations

import asyncio
import time
from typing import TypedDict


class ModelStatus(TypedDict):
    state: str
    message: str
    updated_at: float


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


def update_model_status(key: str, state: str, message: str | None = None) -> None:
    if key not in _MODEL_STATUS:
        return

    entry = _MODEL_STATUS[key]
    entry["state"] = state
    entry["message"] = message or entry["message"]
    entry["updated_at"] = time.time()


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
    start_time = time.time()
    while True:
        if all(info["state"] == "ready" for info in _MODEL_STATUS.values()):
            return True
        if timeout is not None and (time.time() - start_time) >= timeout:
            return False
        await asyncio.sleep(0.5)
