import { NextResponse } from 'next/server';
import { AccessToken, type AccessTokenOptions, type VideoGrant } from 'livekit-server-sdk';
import fs from 'node:fs';
import path from 'node:path';
import { RoomConfiguration } from '@livekit/protocol';

type ConnectionDetails = {
  serverUrl: string;
  roomName: string;
  participantName: string;
  participantToken: string;
};

const ROOT_ENV_PATH = path.resolve(process.cwd(), '..', '.env');

type EnvMap = Record<string, string>;

function parseEnv(content: string): EnvMap {
  const env: EnvMap = {};
  const lines = content.split(/\r?\n/);
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const idx = trimmed.indexOf('=');
    if (idx === -1) continue;
    const key = trimmed.slice(0, idx).trim();
    let value = trimmed.slice(idx + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    env[key] = value;
  }
  return env;
}

function loadRootEnv(): EnvMap {
  try {
    const content = fs.readFileSync(ROOT_ENV_PATH, 'utf8');
    return parseEnv(content);
  } catch {
    return {};
  }
}

const ROOT_ENV = loadRootEnv();

function getEnv(key: string): string | undefined {
  return process.env[key] ?? ROOT_ENV[key];
}

// NOTE: prefer repo-root .env; .env.local is optional for local-only overrides.
const API_KEY = getEnv('LIVEKIT_API_KEY');
const API_SECRET = getEnv('LIVEKIT_API_SECRET');
const LIVEKIT_URL = getEnv('LIVEKIT_URL');
const LIVEKIT_PUBLIC_URL = getEnv('NEXT_PUBLIC_LIVEKIT_URL') ?? getEnv('LIVEKIT_PUBLIC_URL');
const FIXED_ROOM_NAME = getEnv('LIVEKIT_ROOM_NAME') ?? 'voice_assistant_room';

// don't cache the results
export const revalidate = 0;

export async function POST(req: Request) {
  try {
    // Parse agent configuration from request body
    const body = await req.json().catch(() => ({}));
    const agentName: string = body?.room_config?.agents?.[0]?.agent_name;

    if (API_KEY === undefined) {
      throw new Error('LIVEKIT_API_KEY is not defined');
    }
    if (API_SECRET === undefined) {
      throw new Error('LIVEKIT_API_SECRET is not defined');
    }
    if (LIVEKIT_URL === undefined && LIVEKIT_PUBLIC_URL === undefined) {
      throw new Error('LIVEKIT_URL is not defined');
    }

    // Generate participant token
    const participantName = 'user';
    const participantIdentity = `voice_assistant_user_${Math.floor(Math.random() * 10_000)}`;
    const roomName = FIXED_ROOM_NAME;

    const participantToken = await createParticipantToken(
      { identity: participantIdentity, name: participantName },
      roomName,
      agentName
    );

    // Return connection details
    const forwardedProto = req.headers.get('x-forwarded-proto');
    const isHttps = forwardedProto === 'https' || req.url.startsWith('https://');
    const host = req.headers.get('host') || 'localhost';
    const hostname = host.split(':')[0];

    const serverUrl =
      isHttps && LIVEKIT_PUBLIC_URL
        ? LIVEKIT_PUBLIC_URL
        : isHttps
          ? (LIVEKIT_URL ?? `wss://${hostname}`)
          : `ws://${hostname}:7880`;

    const data: ConnectionDetails = {
      serverUrl,
      roomName,
      participantToken: participantToken,
      participantName,
    };
    const headers = new Headers({
      'Cache-Control': 'no-store',
    });
    return NextResponse.json(data, { headers });
  } catch (error) {
    if (error instanceof Error) {
      console.error(error);
      return new NextResponse(error.message, { status: 500 });
    }
  }
}

function createParticipantToken(
  userInfo: AccessTokenOptions,
  roomName: string,
  agentName?: string
): Promise<string> {
  const at = new AccessToken(API_KEY, API_SECRET, {
    ...userInfo,
    ttl: '15m',
  });
  const grant: VideoGrant = {
    room: roomName,
    roomJoin: true,
    canPublish: true,
    canPublishData: true,
    canSubscribe: true,
  };
  at.addGrant(grant);

  if (agentName) {
    at.roomConfig = new RoomConfiguration({
      agents: [{ agentName }],
    });
  }

  return at.toJwt();
}
