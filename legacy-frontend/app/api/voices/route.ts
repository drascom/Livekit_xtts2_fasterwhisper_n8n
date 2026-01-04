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

export const revalidate = 0;

export async function GET() {
  if (typeof WEBHOOK_URL !== 'string' || WEBHOOK_URL.length === 0) {
    return new NextResponse('Webhook URL is not configured', { status: 500 });
  }

  const endpoint = new URL('/voices', WEBHOOK_URL).toString();

  try {
    const response = await fetch(endpoint, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
      cache: 'no-store',
    });

    const contentType = response.headers.get('content-type') || '';
    const data = contentType.includes('application/json') ? await response.json() : null;

    if (!response.ok) {
      const detail =
        typeof data?.detail === 'string'
          ? data.detail
          : `Failed to get voices (status ${response.status})`;
      return new NextResponse(detail, { status: response.status });
    }

    const headers = new Headers({ 'Cache-Control': 'no-store' });
    return NextResponse.json(data ?? { voices: [] }, { headers });
  } catch (error) {
    console.error('Failed to fetch voices:', error);
    return new NextResponse('Failed to connect to voice agent', { status: 502 });
  }
}
