'use client';

import { useEffect, useState } from 'react';

export interface StartupStatus {
  ready: boolean;
  message?: string;
  models?: Record<string, { state: string; message: string }>;
  timestamp?: number;
}

export function useStartupStatus(pollIntervalMs = 4000) {
  const [status, setStatus] = useState<StartupStatus | null>(null);

  useEffect(() => {
    let isMounted = true;
    let timer: ReturnType<typeof setInterval>;

    const fetchStatus = async () => {
      try {
        const response = await fetch('/api/agent-status', { cache: 'no-store' });
        if (!response.ok) {
          throw new Error(`Status request failed: ${response.status}`);
        }
        const payload = await response.json();
        if (!isMounted) return;
        setStatus({
          ready: Boolean(payload?.ready),
          message: payload?.message,
          models: payload?.models,
          timestamp: payload?.timestamp ?? Date.now(),
        });
      } catch (error) {
        if (!isMounted) return;
        setStatus({
          ready: false,
          message: (error as Error).message,
          timestamp: Date.now(),
        });
      }
    };

    fetchStatus();
    timer = setInterval(fetchStatus, pollIntervalMs);
    return () => {
      isMounted = false;
      clearInterval(timer);
    };
  }, [pollIntervalMs]);

  return status;
}
