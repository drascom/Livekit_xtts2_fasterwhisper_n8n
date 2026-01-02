import asyncio
import logging
import os
import time
from dataclasses import dataclass, field

import httpx  # For making a synchronous-style API call to Agent Mind
from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

# Note: In a real-world scenario, audio streaming would require specialized 
# libraries and error handling, but this simulates the API contract.

logger = logging.getLogger(__name__)

app = FastAPI()

PAUSE_THRESHOLD_SECONDS = float(os.getenv("STT_PAUSE_THRESHOLD", "2.0"))
AGENT_QUERY_URL = os.getenv("AGENT_QUERY_URL", "http://voice-agent:8889/agent/query")


@dataclass
class RoomState:
    buffer: bytearray = field(default_factory=bytearray)
    last_activity: float = 0.0
    watcher: asyncio.Task | None = None


_room_states: dict[str, RoomState] = {}

# OpenAI-compatible transcription endpoint for LiveKit Agents
@app.post("/v1/audio/transcriptions")
async def transcribe_audio(
    file: UploadFile = File(...),
    model: str | None = Form(None),
    language: str | None = Form(None),
    prompt: str | None = Form(None),
    temperature: float | None = Form(None),
    response_format: str | None = Form(None),
):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="No audio data received")

    # Placeholder transcript until real STT is integrated
    dummy_transcript = "What is the weather like in London?"
    return {"text": dummy_transcript}

class AgentQueryRequest(BaseModel):
    transcript: str
    room_name: str # Context needed for Agent Mind
    
class AgentQueryResponse(BaseModel):
    response_text: str # Final text from LLM
    response_audio_url: str # Placeholder for TTS audio URL

@app.post("/stt/stream")
async def handle_stt_stream(request: Request):
    """
    Receives an audio stream from the LiveKit Bridge, simulates STT, 
    and forwards the resulting transcript to the Agent Mind.
    """
    # 1. Simulate receiving and processing the audio stream
    # In a real app, this would process chunks until a full sentence/turn is detected
    try:
        # Read the full body (simulating an audio stream transfer)
        body = await request.body()
        if not body:
            raise ValueError("No audio data received.")
            
        # Placeholder for STT logic: a dummy transcript
        # The LiveKit Bridge will also need to send room context, which is missing here
        # For a minimal API contract, we'll assume the room_name is passed via a header/query param
        # We will use a dummy transcript for now.
        dummy_transcript = "What is the weather like in London?"
        room_name = request.headers.get("X-Room-Name", "voice_assistant_room")

    except Exception as e:
        print(f"Error receiving/processing audio: {e}")
        return {"status": "error", "message": str(e)}

    # 2. Forward transcript to Agent Mind
    agent_mind_url = "http://voice-agent:8889/agent/query" # Internal DNS/Port
    
    # Using httpx for a synchronous-style call to the next service
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            agent_response = await client.post(
                agent_mind_url, 
                json=AgentQueryRequest(
                    transcript=dummy_transcript, 
                    room_name=room_name
                ).model_dump()
            )
            agent_response.raise_for_status()
            
            # 3. Return Agent Mind's response
            return agent_response.json()
            
        except httpx.HTTPStatusError as e:
            print(f"Agent Mind failed: {e.response.text}")
            raise HTTPException(status_code=500, detail="Agent Mind service error.")
        except Exception as e:
            print(f"Error calling Agent Mind: {e}")
            raise HTTPException(status_code=500, detail="Failed to connect to Agent Mind.")

# Placeholder for eventual media serving endpoint if needed
# @app.get("/media/{audio_file}")
# async def serve_media(audio_file: str):
#     ...
