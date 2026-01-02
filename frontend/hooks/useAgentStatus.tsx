'use client';

import { useEffect, useState } from 'react';
import { RoomEvent } from 'livekit-client';
import { useSessionContext } from '@livekit/components-react';

export interface AgentStatusState {
  status: string;
  message: string;
  updatedAt: number;
}

interface AgentStatusPayload {
  type?: string;
  status?: string;
  message?: string;
}

export function useAgentStatus(): AgentStatusState | null {
  const { room, isConnected } = useSessionContext();
  const [state, setState] = useState<AgentStatusState | null>(null);

  useEffect(() => {
    if (!room || !isConnected) {
      setState(null);
      return;
    }

    const handleData = (payload: Uint8Array, _participant: unknown, _kind: unknown, topic?: string) => {
      if (topic !== 'agent_status') {
        return;
      }

      try {
        const text = new TextDecoder().decode(payload);
        const data = JSON.parse(text) as AgentStatusPayload;
        if (data?.type !== 'agent_status' || !data.status) {
          return;
        }
        setState({
          status: data.status,
          message: data.message ?? '',
          updatedAt: Date.now(),
        });
      } catch {
        return;
      }
    };

    room.on(RoomEvent.DataReceived, handleData);
    return () => {
      room.off(RoomEvent.DataReceived, handleData);
    };
  }, [room, isConnected]);

  return state;
}
