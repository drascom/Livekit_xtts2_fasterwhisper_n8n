import { API_BASE_URL } from "./config";

export interface TokenResponse {
  token: string;
  room_name: string;
  livekit_url: string;
  user_identity: string;
}

export interface StatusResponse {
  status: string;
  agent_ready: boolean;
  active_sessions: number;
  livekit_connected: boolean;
  speech_server_available: boolean;
}

export interface Settings {
  agent_name: string;
  tts_voice: string;
  tts_voice_tr: string;
  llm_model: string;
  temperature: number;
  num_ctx: number;
  max_turns: number;
  enable_mcp: boolean;
  enable_web_search: boolean;
}

export interface Voice {
  id: string;
  name: string;
  language: string;
}

export interface Model {
  id: string;
  name: string;
}

// Get connection token
export async function getToken(userName: string, roomName?: string): Promise<TokenResponse> {
  const response = await fetch(`${API_BASE_URL}/api/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_name: userName, room_name: roomName }),
  });

  if (!response.ok) {
    throw new Error(`Failed to get token: ${response.statusText}`);
  }

  return response.json();
}

// Get agent status
export async function getStatus(): Promise<StatusResponse> {
  const response = await fetch(`${API_BASE_URL}/api/status`);

  if (!response.ok) {
    throw new Error(`Failed to get status: ${response.statusText}`);
  }

  return response.json();
}

// Get settings
export async function getSettings(): Promise<Settings> {
  const response = await fetch(`${API_BASE_URL}/api/settings`);

  if (!response.ok) {
    throw new Error(`Failed to get settings: ${response.statusText}`);
  }

  return response.json();
}

// Update settings
export async function updateSettings(settings: Partial<Settings>): Promise<Settings> {
  const response = await fetch(`${API_BASE_URL}/api/settings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings),
  });

  if (!response.ok) {
    throw new Error(`Failed to update settings: ${response.statusText}`);
  }

  return response.json();
}

// Get available voices
export async function getVoices(): Promise<Voice[]> {
  const response = await fetch(`${API_BASE_URL}/api/voices`);

  if (!response.ok) {
    throw new Error(`Failed to get voices: ${response.statusText}`);
  }

  return response.json();
}

// Get available models
export async function getModels(): Promise<Model[]> {
  const response = await fetch(`${API_BASE_URL}/api/models`);

  if (!response.ok) {
    throw new Error(`Failed to get models: ${response.statusText}`);
  }

  return response.json();
}

// Wake agent in room
export async function wakeAgent(roomName: string, message?: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/wake`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ room_name: roomName, message }),
  });

  if (!response.ok) {
    throw new Error(`Failed to wake agent: ${response.statusText}`);
  }
}
