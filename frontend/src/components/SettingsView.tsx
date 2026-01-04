"use client";

import { useEffect, useState } from "react";
import { getModels, getSettings, updateSettings } from "@/lib/api";

interface SettingsViewProps {
  onBack: () => void;
}

type FormState = {
  llm_model: string;
  temperature: string;
  num_ctx: string;
  max_turns: string;
};

const DEFAULT_FORM: FormState = {
  llm_model: "",
  temperature: "0.7",
  num_ctx: "4096",
  max_turns: "10",
};

export function SettingsView({ onBack }: SettingsViewProps) {
  const [form, setForm] = useState<FormState>(DEFAULT_FORM);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string>();
  const [success, setSuccess] = useState<string>();
  const [models, setModels] = useState<string[]>([]);

  useEffect(() => {
    let isMounted = true;
    Promise.all([getSettings(), getModels()])
      .then(([settings, availableModels]) => {
        if (!isMounted) return;
        setModels(availableModels.map((model) => model.id));
        setForm({
          llm_model: settings.llm_model || "",
          temperature: String(settings.temperature ?? 0.7),
          num_ctx: String(settings.num_ctx ?? 4096),
          max_turns: String(settings.max_turns ?? 10),
        });
      })
      .catch((err) => {
        if (!isMounted) return;
        setError(err instanceof Error ? err.message : "Failed to load settings");
      })
      .finally(() => {
        if (!isMounted) return;
        setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const handleChange =
    (key: keyof FormState) => (e: React.ChangeEvent<HTMLInputElement>) => {
      setForm((prev) => ({ ...prev, [key]: e.target.value }));
    };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(undefined);
    setSuccess(undefined);

    const temperature = Number(form.temperature);
    const numCtx = Number(form.num_ctx);
    const maxTurns = Number(form.max_turns);

    if (Number.isNaN(temperature)) {
      setError("Temperature must be a number.");
      return;
    }
    if (Number.isNaN(numCtx) || numCtx <= 0) {
      setError("Context size must be a positive number.");
      return;
    }
    if (Number.isNaN(maxTurns) || maxTurns <= 0) {
      setError("Max turns must be a positive number.");
      return;
    }

    setIsSaving(true);
    try {
      await updateSettings({
        llm_model: form.llm_model.trim(),
        temperature,
        num_ctx: numCtx,
        max_turns: maxTurns,
      });
      setSuccess("Settings saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save settings");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 to-gray-800">
      <div className="bg-gray-800 rounded-2xl p-8 shadow-2xl max-w-lg w-full mx-4">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-semibold text-white">Settings</h1>
            <p className="text-sm text-gray-400">Configure your model parameters</p>
          </div>
          <button
            onClick={onBack}
            className="text-sm text-blue-400 hover:text-blue-300"
          >
            Back
          </button>
        </div>

        {isLoading ? (
          <div className="text-gray-400">Loading settings...</div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="llm_model" className="block text-sm font-medium text-gray-300 mb-2">
                Ollama model name
              </label>
              <select
                id="llm_model"
                value={form.llm_model}
                onChange={handleChange("llm_model")}
                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="" disabled>
                  Select a model
                </option>
                {models.map((modelId) => (
                  <option key={modelId} value={modelId}>
                    {modelId}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label htmlFor="temperature" className="block text-sm font-medium text-gray-300 mb-2">
                  Temperature
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="2"
                  id="temperature"
                  value={form.temperature}
                  onChange={handleChange("temperature")}
                  className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label htmlFor="num_ctx" className="block text-sm font-medium text-gray-300 mb-2">
                  Context size
                </label>
                <input
                  type="number"
                  step="1"
                  min="1"
                  id="num_ctx"
                  value={form.num_ctx}
                  onChange={handleChange("num_ctx")}
                  className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label htmlFor="max_turns" className="block text-sm font-medium text-gray-300 mb-2">
                  Max turns
                </label>
                <input
                  type="number"
                  step="1"
                  min="1"
                  id="max_turns"
                  value={form.max_turns}
                  onChange={handleChange("max_turns")}
                  className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
            </div>

            {error && (
              <div className="bg-red-900/50 border border-red-500 text-red-200 px-4 py-3 rounded-lg text-sm">
                {error}
              </div>
            )}

            {success && (
              <div className="bg-green-900/40 border border-green-500 text-green-200 px-4 py-3 rounded-lg text-sm">
                {success}
              </div>
            )}

            <button
              type="submit"
              disabled={isSaving}
              className="w-full py-4 bg-gradient-to-r from-blue-500 to-purple-600 text-white font-semibold rounded-lg hover:from-blue-600 hover:to-purple-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
            >
              {isSaving ? "Saving..." : "Save settings"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
