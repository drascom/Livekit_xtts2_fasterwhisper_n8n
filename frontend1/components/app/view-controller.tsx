'use client';

import { useCallback, useRef } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { useSessionContext } from '@livekit/components-react';
import type { AppConfig } from '@/app-config';
import { SessionView } from '@/components/app/session-view';
import { WelcomeView } from '@/components/app/welcome-view';

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

  const handleStartCall = useCallback(async () => {
    await start();

    const roomName = room?.name;
    if (!roomName || lastWakeRoom.current === roomName) {
      return;
    }

    lastWakeRoom.current = roomName;
    try {
      await fetch('/api/wake', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ room_name: roomName }),
      });
    } catch (error) {
      console.error('Failed to wake agent', error);
    }
  }, [start, room]);

  return (
    <AnimatePresence mode="wait">
      {/* Welcome view */}
      {!isConnected && (
        <MotionWelcomeView
          key="welcome"
          {...VIEW_MOTION_PROPS}
          startButtonText={appConfig.startButtonText}
          onStartCall={handleStartCall}
        />
      )}
      {/* Session view */}
      {isConnected && (
        <MotionSessionView key="session-view" {...VIEW_MOTION_PROPS} appConfig={appConfig} />
      )}
    </AnimatePresence>
  );
}
