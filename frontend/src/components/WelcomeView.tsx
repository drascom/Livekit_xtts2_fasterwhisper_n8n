"use client";

import { useState, useEffect } from "react";

interface WelcomeViewProps {
  onConnect: (userName: string) => void;
  isConnecting: boolean;
  error?: string;
  savedName?: string;
  onOpenSettings: () => void;
}

export function WelcomeView({
  onConnect,
  isConnecting,
  error,
  savedName,
  onOpenSettings,
}: WelcomeViewProps) {
  const [userName, setUserName] = useState("");
  const [isEditing, setIsEditing] = useState(!savedName);

  // Update input when savedName changes
  useEffect(() => {
    if (savedName) {
      setUserName(savedName);
      setIsEditing(false);
    }
  }, [savedName]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onConnect(userName || "User");
  };

  const handleQuickStart = () => {
    onConnect(savedName || "User");
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 to-gray-800">
      <div className="bg-gray-800 rounded-2xl p-8 shadow-2xl max-w-md w-full mx-4 relative">
        <button
          type="button"
          onClick={onOpenSettings}
          className="absolute top-4 right-4 text-gray-400 hover:text-white transition-colors"
          aria-label="Open settings"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 6.75a5.25 5.25 0 100 10.5 5.25 5.25 0 000-10.5z"
            />
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19.5 12a7.5 7.5 0 00-.09-1.17l1.79-1.39a.75.75 0 00.18-1.02l-1.7-2.94a.75.75 0 00-.96-.34l-2.12.85a7.5 7.5 0 00-2.02-1.17l-.32-2.26A.75.75 0 0011.5 1.5h-3a.75.75 0 00-.74.61l-.32 2.26a7.5 7.5 0 00-2.02 1.17l-2.12-.85a.75.75 0 00-.96.34L1.64 7.97a.75.75 0 00.18 1.02l1.79 1.39A7.5 7.5 0 003.5 12c0 .4.03.79.09 1.17l-1.79 1.39a.75.75 0 00-.18 1.02l1.7 2.94c.2.34.6.48.96.34l2.12-.85c.61.5 1.29.9 2.02 1.17l.32 2.26c.06.36.38.61.74.61h3c.36 0 .68-.25.74-.61l.32-2.26c.73-.27 1.41-.67 2.02-1.17l2.12.85c.36.14.76 0 .96-.34l1.7-2.94a.75.75 0 00-.18-1.02l-1.79-1.39c.06-.38.09-.77.09-1.17z"
            />
          </svg>
        </button>
        <div className="text-center mb-8">
          <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full mx-auto mb-4 flex items-center justify-center">
            <svg
              className="w-10 h-10 text-white"
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
          <h1 className="text-3xl font-bold text-white mb-2">Geveze</h1>
          <p className="text-gray-400">AI Voice Assistant</p>
        </div>

        {/* Show welcome back message if we have a saved name */}
        {savedName && !isEditing ? (
          <div className="space-y-4">
            <div className="text-center">
              <p className="text-gray-300 mb-1 whitespace-nowrap">
                Welcome back,{" "}
                <span className="inline-flex items-end gap-2">
                  <span className="text-xl font-semibold text-white capitalize">{savedName}</span>
                  <button
                    onClick={() => setIsEditing(true)}
                    className="text-xs text-blue-400 hover:text-blue-300"
                  >
                    Change name
                  </button>
                </span>
              </p>
            </div>

            {error && (
              <div className="bg-red-900/50 border border-red-500 text-red-200 px-4 py-3 rounded-lg text-sm">
                {error}
              </div>
            )}

            <button
              onClick={handleQuickStart}
              disabled={isConnecting}
              className="w-full py-4 bg-gradient-to-r from-blue-500 to-purple-600 text-white font-semibold rounded-lg hover:from-blue-600 hover:to-purple-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
            >
              {isConnecting ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                      fill="none"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  Connecting...
                </span>
              ) : (
                "Start Call"
              )}
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-gray-300 mb-2">
                Your Name
              </label>
              <input
                type="text"
                id="name"
                value={userName}
                onChange={(e) => setUserName(e.target.value)}
                placeholder="Enter your name"
                autoFocus
                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            {error && (
              <div className="bg-red-900/50 border border-red-500 text-red-200 px-4 py-3 rounded-lg text-sm">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={isConnecting}
              className="w-full py-4 bg-gradient-to-r from-blue-500 to-purple-600 text-white font-semibold rounded-lg hover:from-blue-600 hover:to-purple-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
            >
              {isConnecting ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                      fill="none"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  Connecting...
                </span>
              ) : (
                "Start Call"
              )}
            </button>

            {savedName && (
              <button
                type="button"
                onClick={() => setIsEditing(false)}
                className="w-full text-sm text-gray-400 hover:text-gray-300"
              >
                Cancel
              </button>
            )}
          </form>
        )}

        <p className="mt-6 text-center text-gray-500 text-sm">
          Click to start a voice conversation with the AI assistant
        </p>
      </div>
    </div>
  );
}
