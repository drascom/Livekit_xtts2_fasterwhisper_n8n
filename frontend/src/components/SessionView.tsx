"use client";

import {
  LiveKitRoom,
  RoomAudioRenderer,
  useRoomContext,
  useParticipants,
  useLocalParticipant,
  useTrackToggle,
  useTracks,
} from "@livekit/components-react";
import { Track } from "livekit-client";
import { useCallback, useState } from "react";

interface SessionViewProps {
  token: string;
  serverUrl: string;
  roomName: string;
  userName: string;
  onDisconnect: () => void;
  onChangeName?: () => void;
}

export function SessionView({
  token,
  serverUrl,
  roomName,
  userName,
  onDisconnect,
  onChangeName,
}: SessionViewProps) {
  return (
    <LiveKitRoom
      token={token}
      serverUrl={serverUrl}
      connect={true}
      audio={true}
      video={false}
      onDisconnected={onDisconnect}
      className="min-h-screen bg-gray-900"
    >
      <RoomContent roomName={roomName} userName={userName} onDisconnect={onDisconnect} onChangeName={onChangeName} />
      <RoomAudioRenderer />
    </LiveKitRoom>
  );
}

function RoomContent({
  roomName,
  userName,
  onDisconnect,
  onChangeName,
}: {
  roomName: string;
  userName: string;
  onDisconnect: () => void;
  onChangeName?: () => void;
}) {
  const room = useRoomContext();
  const participants = useParticipants();
  const { localParticipant } = useLocalParticipant();
  const [isAgentSpeaking, setIsAgentSpeaking] = useState(false);

  // Track agent speaking state
  const audioTracks = useTracks([Track.Source.Microphone]);

  // Find agent participant
  const agentParticipant = participants.find(
    (p) => p.identity !== localParticipant?.identity
  );

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between max-w-4xl mx-auto">
          <div>
            <h1 className="text-xl font-semibold text-white">Geveze</h1>
            <p className="text-sm text-gray-400">Room: {roomName}</p>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 whitespace-nowrap">
              <span className="text-sm text-white">{userName}</span>
              {onChangeName && (
                <button
                  onClick={onChangeName}
                  className="text-xs text-blue-400 hover:text-blue-300"
                >
                  change
                </button>
              )}
            </div>
            <div className="flex items-center gap-2">
              <span
                className={`w-2 h-2 rounded-full ${
                  room.state === "connected" ? "bg-green-500" : "bg-yellow-500"
                }`}
              />
              <span className="text-sm text-gray-400 capitalize">{room.state}</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex items-center justify-center p-8">
        <div className="text-center">
          {/* Agent Avatar */}
          <div className="relative mb-8">
            <div
              className={`w-32 h-32 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 mx-auto flex items-center justify-center transition-all duration-300 ${
                isAgentSpeaking ? "scale-110 shadow-lg shadow-blue-500/50" : ""
              }`}
            >
              <svg
                className="w-16 h-16 text-white"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
                />
              </svg>
            </div>
            {/* Speaking indicator */}
            {isAgentSpeaking && (
              <div className="absolute -bottom-2 left-1/2 -translate-x-1/2">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                  <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                  <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                </div>
              </div>
            )}
          </div>

          {/* Status */}
          <h2 className="text-2xl font-semibold text-white mb-2">
            {agentParticipant ? "Agent Connected" : "Waiting for Agent..."}
          </h2>
          <p className="text-gray-400 mb-8">
            {agentParticipant
              ? "Speak to start a conversation"
              : "The AI assistant is joining..."}
          </p>

          {/* Participants */}
          <div className="flex justify-center gap-4 mb-8">
            {participants.map((participant) => (
              <div
                key={participant.identity}
                className="bg-gray-800 rounded-lg px-4 py-2 text-sm"
              >
                <span className="text-gray-300">
                  {participant.name || participant.identity}
                </span>
                {participant.identity === localParticipant?.identity && (
                  <span className="text-gray-500 ml-2">(You)</span>
                )}
              </div>
            ))}
          </div>
        </div>
      </main>

      {/* Control Bar */}
      <ControlBar onDisconnect={onDisconnect} />
    </div>
  );
}

function ControlBar({ onDisconnect }: { onDisconnect: () => void }) {
  const { toggle: toggleMic, enabled: micEnabled } = useTrackToggle({
    source: Track.Source.Microphone,
  });

  return (
    <footer className="bg-gray-800 border-t border-gray-700 px-6 py-4">
      <div className="flex items-center justify-center gap-4 max-w-4xl mx-auto">
        {/* Microphone Toggle */}
        <button
          onClick={() => toggleMic()}
          className={`p-4 rounded-full transition-colors ${
            micEnabled
              ? "bg-gray-700 hover:bg-gray-600 text-white"
              : "bg-red-600 hover:bg-red-700 text-white"
          }`}
          title={micEnabled ? "Mute microphone" : "Unmute microphone"}
        >
          {micEnabled ? (
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
              />
            </svg>
          ) : (
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M17 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2"
              />
            </svg>
          )}
        </button>

        {/* Disconnect Button */}
        <button
          onClick={onDisconnect}
          className="p-4 rounded-full bg-red-600 hover:bg-red-700 text-white transition-colors"
          title="End call"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M16 8l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2M5 3a2 2 0 00-2 2v1c0 8.284 6.716 15 15 15h1a2 2 0 002-2v-3.28a1 1 0 00-.684-.948l-4.493-1.498a1 1 0 00-1.21.502l-1.13 2.257a11.042 11.042 0 01-5.516-5.517l2.257-1.128a1 1 0 00.502-1.21L9.228 3.683A1 1 0 008.279 3H5z"
            />
          </svg>
        </button>
      </div>
    </footer>
  );
}
