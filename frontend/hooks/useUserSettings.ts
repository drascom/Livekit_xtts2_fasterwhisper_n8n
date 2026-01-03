'use client';

import { useCallback, useEffect, useState } from 'react';

export interface UserSettings {
  agent_name: string;
  tts_voice: string;
  tts_language: string; // "auto", "en", or "tr"
  prompt: string;
  wake_greetings: string[];
  temperature: number;
  model: string;
  num_ctx: number;
  max_turns: number;
  tool_cache_size: number;
}

const STORAGE_KEY = 'geveze_user_settings';

export const DEFAULT_USER_SETTINGS: UserSettings = {
  agent_name: 'Cal',
  tts_voice: 'ayhan',
  tts_language: 'auto',
  prompt: 'default',
  wake_greetings: [
    "Hey, what's up?",
    'Hi there!',
    'Yeah?',
    'What can I do for you?',
    'Hey!',
    'Yo!',
    "What's up?",
  ],
  temperature: 0.7,
  model: 'ministral-3:8b',
  num_ctx: 8192,
  max_turns: 20,
  tool_cache_size: 3,
};

function loadSettingsFromStorage(): UserSettings {
  if (typeof window === 'undefined') {
    return DEFAULT_USER_SETTINGS;
  }

  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      return { ...DEFAULT_USER_SETTINGS, ...parsed };
    }
  } catch (err) {
    console.error('Failed to load settings from localStorage:', err);
  }

  return DEFAULT_USER_SETTINGS;
}

function saveSettingsToStorage(settings: UserSettings): void {
  if (typeof window === 'undefined') {
    return;
  }

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  } catch (err) {
    console.error('Failed to save settings to localStorage:', err);
  }
}

export function useUserSettings() {
  const [settings, setSettings] = useState<UserSettings>(DEFAULT_USER_SETTINGS);
  const [isLoaded, setIsLoaded] = useState(false);

  // Load settings from localStorage on mount
  useEffect(() => {
    const stored = loadSettingsFromStorage();
    setSettings(stored);
    setIsLoaded(true);
  }, []);

  const updateSettings = useCallback((newSettings: Partial<UserSettings>) => {
    setSettings((prev) => {
      const updated = { ...prev, ...newSettings };
      saveSettingsToStorage(updated);
      return updated;
    });
  }, []);

  const saveSettings = useCallback((newSettings: UserSettings) => {
    setSettings(newSettings);
    saveSettingsToStorage(newSettings);
  }, []);

  const resetSettings = useCallback(() => {
    setSettings(DEFAULT_USER_SETTINGS);
    saveSettingsToStorage(DEFAULT_USER_SETTINGS);
  }, []);

  return {
    settings,
    isLoaded,
    updateSettings,
    saveSettings,
    resetSettings,
  };
}

// Export for use outside of React (e.g., in API calls)
export function getUserSettings(): UserSettings {
  return loadSettingsFromStorage();
}
