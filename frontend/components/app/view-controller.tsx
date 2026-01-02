'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { useSessionContext } from '@livekit/components-react';
import type { AppConfig } from '@/app-config';
import { SessionView } from '@/components/app/session-view';
import { WelcomeView } from '@/components/app/welcome-view';
import { useAgentStatus } from '@/hooks/useAgentStatus';
import { useStartupStatus } from '@/hooks/useStartupStatus';

const MotionWelcomeView = motion.create(WelcomeView);
const MotionSessionView = motion.create(SessionView);

const VIEW_MOTION_PROPS = {
  variants: {
    visible: {
      opacity: 1,
    },
    hidden: {
      opacity: 0,
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
  transition: {
    duration: 0.5,
    ease: 'linear',
  },
};

interface ViewControllerProps {
  appConfig: AppConfig;
}

export function ViewController({ appConfig }: ViewControllerProps) {
  const { isConnected, start, room } = useSessionContext();
  const lastWakeRoom = useRef<string | null>(null);
  const agentStatus = useAgentStatus();
  const startupStatus = useStartupStatus();
  const isAgentReady = startupStatus?.ready ?? false;
  const [pendingWakeRoom, setPendingWakeRoom] = useState<string | null>(null);

  const handleStartCall = useCallback(async () => {
    if (!isAgentReady) {
      return;
    }

    await start();

    const roomName = room?.name;
    if (!roomName || lastWakeRoom.current === roomName) {
      return;
    }

    lastWakeRoom.current = roomName;
    if (agentStatus?.status === 'agent_ready') {
      try {
        await fetch('/api/wake', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ room_name: roomName }),
        });
      } catch (error) {
        console.error('Failed to wake agent', error);
      }
      return;
    }

    setPendingWakeRoom(roomName);
  }, [start, room, agentStatus?.status, isAgentReady]);

  useEffect(() => {
    if (!pendingWakeRoom || agentStatus?.status !== 'agent_ready') {
      return;
    }

    const roomName = pendingWakeRoom;
    setPendingWakeRoom(null);

    fetch('/api/wake', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ room_name: roomName }),
    }).catch((error) => {
      console.error('Failed to wake agent', error);
    });
  }, [pendingWakeRoom, agentStatus?.status]);

  return (
    <AnimatePresence mode="wait">
      {/* Welcome view */}
      {!isConnected && (
        <MotionWelcomeView
          key="welcome"
          {...VIEW_MOTION_PROPS}
          startButtonText={appConfig.startButtonText}
          onStartCall={handleStartCall}
          statusMessage={startupStatus?.message}
          agentReady={isAgentReady}
        />
      )}
      {/* Session view */}
      {isConnected && (
        <MotionSessionView
          key="session-view"
          {...VIEW_MOTION_PROPS}
          appConfig={appConfig}
          agentStatus={agentStatus}
        />
      )}
    </AnimatePresence>
  );
}
