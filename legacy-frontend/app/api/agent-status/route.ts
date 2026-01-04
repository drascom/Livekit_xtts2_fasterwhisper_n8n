import { NextResponse } from 'next/server';

const AGENT_STATUS_URL =
  process.env.VOICE_AGENT_STATUS_URL ?? "http://voice-agent:8889/status";

export async function GET() {
  try {
    const response = await fetch(AGENT_STATUS_URL, {
      cache: "no-store",
    });

    if (!response.ok) {
      throw new Error(`Voice agent status request failed: ${response.status}`);
    }

    const status = await response.json();
    return NextResponse.json(status);
  } catch (error) {
    return NextResponse.json(
      {
        ready: false,
        message: (error as Error).message || "Failed to fetch agent status",
      },
      { status: 503 }
    );
  }
}
