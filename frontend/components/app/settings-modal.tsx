'use client';

import { useCallback, useEffect, useState } from 'react';
import { Button } from '@/components/livekit/button';
import { DEFAULT_USER_SETTINGS, type UserSettings, getUserSettings } from '@/hooks/useUserSettings';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const STORAGE_KEY = 'geveze_user_settings';

export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const [settings, setSettings] = useState<UserSettings>(DEFAULT_USER_SETTINGS);
  const [voices, setVoices] = useState<string[]>([]);
  const [models, setModels] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadSettings = useCallback(() => {
    setLoading(true);
    setError(null);
    try {
      // Load settings from localStorage (per-user settings)
      const userSettings = getUserSettings();
      setSettings(userSettings);
    } catch (err) {
      console.error('Failed to load settings:', err);
      setError('Failed to load settings');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadVoices = useCallback(async () => {
    try {
      const res = await fetch('/api/voices');
      if (res.ok) {
        const data = await res.json();
        setVoices(data.voices || []);
      }
    } catch (err) {
      console.error('Failed to load voices:', err);
    }
  }, []);

  const loadModels = useCallback(async () => {
    try {
      const res = await fetch('/api/models');
      if (res.ok) {
        const data = await res.json();
        setModels(data.models || []);
      }
    } catch (err) {
      console.error('Failed to load models:', err);
    }
  }, []);

  // Load settings when modal opens
  useEffect(() => {
    if (isOpen) {
      loadSettings();
      loadVoices();
      loadModels();
    }
  }, [isOpen, loadSettings, loadVoices, loadModels]);

  const saveSettings = async () => {
    setSaving(true);
    setError(null);
    try {
      // Save settings to localStorage (per-user persistence)
      localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));

      // Also sync to backend for current/future sessions
      try {
        await fetch('/api/settings', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(settings),
        });
      } catch (syncErr) {
        // Backend sync is optional - localStorage is the source of truth
        console.warn('Failed to sync settings to backend:', syncErr);
      }

      onClose();
    } catch (err) {
      console.error('Failed to save settings:', err);
      setError('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const handleSettingChange = <K extends keyof UserSettings>(key: K, value: UserSettings[K]) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-background border-border max-h-[90vh] w-full max-w-2xl overflow-hidden rounded-lg border shadow-xl">
        {/* Header */}
        <div className="border-border flex items-center justify-between border-b p-4">
          <h2 className="text-foreground text-lg font-semibold">Settings</h2>
          <button
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="max-h-[calc(90vh-140px)] space-y-6 overflow-y-auto p-4">
          {error && (
            <div className="bg-destructive/10 text-destructive rounded-md p-3 text-sm">{error}</div>
          )}

          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="border-primary h-8 w-8 animate-spin rounded-full border-b-2"></div>
            </div>
          ) : (
            <>
              {/* Agent Settings */}
              <section>
                <h3 className="text-foreground mb-3 text-sm font-medium">Agent Settings</h3>
                <div className="space-y-3">
                  <div>
                    <label className="text-muted-foreground mb-1 block text-xs">Agent Name</label>
                    <input
                      type="text"
                      value={settings.agent_name}
                      onChange={(e) => handleSettingChange('agent_name', e.target.value)}
                      className="bg-muted border-border text-foreground focus:ring-primary w-full rounded-md border px-3 py-2 text-sm focus:ring-2 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-muted-foreground mb-1 block text-xs">
                      Default Voice
                    </label>
                    <select
                      value={settings.tts_voice}
                      onChange={(e) => handleSettingChange('tts_voice', e.target.value)}
                      className="bg-muted border-border text-foreground focus:ring-primary w-full rounded-md border px-3 py-2 text-sm focus:ring-2 focus:outline-none"
                    >
                      {voices.length > 0 ? (
                        voices.map((voice) => (
                          <option key={voice} value={voice}>
                            {voice}
                          </option>
                        ))
                      ) : (
                        <option value={settings.tts_voice}>{settings.tts_voice}</option>
                      )}
                    </select>
                  </div>
                  <div>
                    <label className="text-muted-foreground mb-1 block text-xs">Language</label>
                    <select
                      value={settings.tts_language}
                      onChange={(e) => handleSettingChange('tts_language', e.target.value)}
                      className="bg-muted border-border text-foreground focus:ring-primary w-full rounded-md border px-3 py-2 text-sm focus:ring-2 focus:outline-none"
                    >
                      <option value="auto">Auto-detect</option>
                      <option value="en">English</option>
                      <option value="tr">Turkish</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-muted-foreground mb-1 block text-xs">LLM Model</label>
                    <select
                      value={settings.model}
                      onChange={(e) => handleSettingChange('model', e.target.value)}
                      className="bg-muted border-border text-foreground focus:ring-primary w-full rounded-md border px-3 py-2 text-sm focus:ring-2 focus:outline-none"
                    >
                      {models.length > 0 ? (
                        models.map((model) => (
                          <option key={model} value={model}>
                            {model}
                          </option>
                        ))
                      ) : (
                        <option value={settings.model}>{settings.model}</option>
                      )}
                    </select>
                  </div>
                  <div>
                    <label className="text-muted-foreground mb-1 block text-xs">Prompt Mode</label>
                    <select
                      value={settings.prompt}
                      onChange={(e) => handleSettingChange('prompt', e.target.value)}
                      className="bg-muted border-border text-foreground focus:ring-primary w-full rounded-md border px-3 py-2 text-sm focus:ring-2 focus:outline-none"
                    >
                      <option value="default">Default</option>
                      <option value="custom">Custom</option>
                    </select>
                  </div>
                </div>
              </section>

              {/* Advanced Settings */}
              <section>
                <h3 className="text-foreground mb-3 text-sm font-medium">Advanced Settings</h3>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-muted-foreground mb-1 block text-xs">
                      Temperature ({settings.temperature})
                    </label>
                    <input
                      type="range"
                      min="0"
                      max="2"
                      step="0.1"
                      value={settings.temperature}
                      onChange={(e) =>
                        handleSettingChange('temperature', parseFloat(e.target.value))
                      }
                      className="w-full"
                    />
                  </div>
                  <div>
                    <label className="text-muted-foreground mb-1 block text-xs">
                      Context Window
                    </label>
                    <input
                      type="number"
                      value={settings.num_ctx}
                      onChange={(e) =>
                        handleSettingChange('num_ctx', parseInt(e.target.value) || 8192)
                      }
                      className="bg-muted border-border text-foreground focus:ring-primary w-full rounded-md border px-3 py-2 text-sm focus:ring-2 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-muted-foreground mb-1 block text-xs">Max Turns</label>
                    <input
                      type="number"
                      value={settings.max_turns}
                      onChange={(e) =>
                        handleSettingChange('max_turns', parseInt(e.target.value) || 20)
                      }
                      className="bg-muted border-border text-foreground focus:ring-primary w-full rounded-md border px-3 py-2 text-sm focus:ring-2 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-muted-foreground mb-1 block text-xs">
                      Tool Cache Size
                    </label>
                    <input
                      type="number"
                      value={settings.tool_cache_size}
                      onChange={(e) =>
                        handleSettingChange('tool_cache_size', parseInt(e.target.value) || 3)
                      }
                      className="bg-muted border-border text-foreground focus:ring-primary w-full rounded-md border px-3 py-2 text-sm focus:ring-2 focus:outline-none"
                    />
                  </div>
                </div>
              </section>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="border-border flex items-center justify-end gap-3 border-t p-4">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="primary" onClick={saveSettings} disabled={saving || loading}>
            {saving ? 'Saving...' : 'Save Settings'}
          </Button>
        </div>
      </div>
    </div>
  );
}
