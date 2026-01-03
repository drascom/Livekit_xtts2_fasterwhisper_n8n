import { NextResponse } from 'next/server';
import fs from 'node:fs';
import path from 'node:path';

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

const WEBHOOK_URL = getEnv('WEBHOOK_URL') ?? 'http://voice-agent:8889';
const AGENT_STATUS_URL = getEnv('VOICE_AGENT_STATUS_URL');

export const revalidate = 0;
export async function GET() {
  try {
    const endpoint = AGENT_STATUS_URL ?? new URL('/status', WEBHOOK_URL).toString();
    const response = await fetch(endpoint, {
      cache: 'no-store',
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
        message: (error as Error).message || 'Failed to fetch agent status',
      },
      { status: 503 }
    );
  }
}
