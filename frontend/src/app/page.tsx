"use client";

import { useState, useCallback, useEffect } from "react";
import { WelcomeView } from "@/components/WelcomeView";
import { SettingsView } from "@/components/SettingsView";
import { SessionView } from "@/components/SessionView";
import { getToken, TokenResponse } from "@/lib/api";

const STORAGE_KEY = "geveze_user_name";

type ViewState = "welcome" | "settings" | "session";

export default function Home() {
  const [view, setView] = useState<ViewState>("welcome");
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string>();
  const [connectionDetails, setConnectionDetails] = useState<TokenResponse | null>(null);
  const [userName, setUserName] = useState("");
  const [savedName, setSavedName] = useState("");

  // Load saved name from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      setSavedName(stored);
      setUserName(stored);
    }
  }, []);

  const handleConnect = useCallback(async (name: string) => {
    setIsConnecting(true);
    setError(undefined);
    const finalName = name || "User";
    setUserName(finalName);

    // Save to localStorage
    localStorage.setItem(STORAGE_KEY, finalName);
    setSavedName(finalName);

    try {
      const details = await getToken(finalName);
      setConnectionDetails(details);
      setView("session");
    } catch (err) {
      console.error("Failed to connect:", err);
      setError(err instanceof Error ? err.message : "Failed to connect to the server");
    } finally {
      setIsConnecting(false);
    }
  }, []);

  const handleDisconnect = useCallback(() => {
    setConnectionDetails(null);
    setView("welcome");
  }, []);

  const handleChangeName = useCallback(() => {
    // Clear saved name and go back to welcome
    setConnectionDetails(null);
    setView("welcome");
  }, []);

  if (view === "settings") {
    return <SettingsView onBack={() => setView("welcome")} />;
  }

  if (view === "welcome" || !connectionDetails) {
    return (
      <WelcomeView
        onConnect={handleConnect}
        isConnecting={isConnecting}
        error={error}
        savedName={savedName}
        onOpenSettings={() => setView("settings")}
      />
    );
  }

  return (
    <SessionView
      token={connectionDetails.token}
      serverUrl={connectionDetails.livekit_url}
      roomName={connectionDetails.room_name}
      userName={userName}
      onDisconnect={handleDisconnect}
      onChangeName={handleChangeName}
    />
  );
}
