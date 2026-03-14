// src/pages/Settings.tsx
import React, { useEffect, useState } from 'react';
import Navbar from '../components/Navbar';
import { settingsAPI } from '../api/client';
import { UserSettings, DEFAULT_SETTINGS } from '../types/settings';
import { applyTheme, storeTheme } from '../utils/theme';

const SETTINGS_CACHE_KEY = 'focuspilot-settings-cache-v1';

function getCachedSettings(): UserSettings {
  try {
    const cached = localStorage.getItem(SETTINGS_CACHE_KEY);
    if (!cached) return DEFAULT_SETTINGS;
    return { ...DEFAULT_SETTINGS, ...JSON.parse(cached) };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

function Settings() {
  const [settings, setSettings]     = useState<UserSettings>(getCachedSettings);
  const [dataStatus, setDataStatus] = useState<any>(null);
  const [loading, setLoading]       = useState(false);
  const [saving, setSaving]         = useState(false);
  const [saved, setSaved]           = useState(false);

  useEffect(() => {
    loadSettings();
    loadDataStatus();
  }, []);

  const loadSettings = async () => {
    setLoading(true);
    try {
      const settingsRes = await settingsAPI.get();
      setSettings(settingsRes.data);
      localStorage.setItem(SETTINGS_CACHE_KEY, JSON.stringify(settingsRes.data));
      applyTheme(settingsRes.data.theme);
      storeTheme(settingsRes.data.theme);
    } catch (error) {
      console.error('Error loading settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadDataStatus = async () => {
    try {
      const dataRes = await settingsAPI.getDataStatus();
      setDataStatus(dataRes.data);
    } catch (error) {
      console.error('Error loading data status:', error);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await settingsAPI.update(settings);
      localStorage.setItem(SETTINGS_CACHE_KEY, JSON.stringify(settings));
      applyTheme(settings.theme);
      storeTheme(settings.theme);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (error) {
      alert('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const update = (key: keyof UserSettings, value: any) => {
    if (key === 'theme') {
      applyTheme(value);
      storeTheme(value);
    }
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100">
        <Navbar />
        <div className="flex items-center justify-center h-64">
          <p className="text-gray-500 text-xl animate-pulse">Loading settings...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <Navbar />

      <main className="max-w-3xl mx-auto px-4 py-8">

        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
            <p className="text-gray-600 mt-1">
              Configure how FocusPilot works for you
            </p>
          </div>
          <button
            onClick={handleSave}
            disabled={saving}
            className={`px-6 py-3 rounded-lg font-semibold transition ${
              saved
                ? 'bg-green-600 text-white'
                : 'bg-blue-600 text-white hover:bg-blue-700'
            } disabled:bg-gray-400`}
          >
            {saving ? 'Saving...' : saved ? 'Saved' : 'Save Changes'}
          </button>
        </div>

        {/* ML Data Status Card */}
        {dataStatus && (
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">
              AI Model Status
            </h2>
            <div className="flex items-center justify-between mb-3">
              <span className="text-gray-700">Data Collection Progress</span>
              <span className="font-semibold text-gray-900">
                {dataStatus.sessions_have}/{dataStatus.sessions_needed} sessions
              </span>
            </div>
            {/* Progress bar */}
            <div className="w-full bg-gray-200 rounded-full h-3 mb-3">
              <div
                className={`h-3 rounded-full transition-all ${
                  dataStatus.progress_pct >= 100
                    ? 'bg-green-500'
                    : dataStatus.progress_pct >= 25
                    ? 'bg-yellow-500'
                    : 'bg-red-500'
                }`}
                style={{ width: `${dataStatus.progress_pct}%` }}
              />
            </div>
            <p className="text-sm text-gray-600">{dataStatus.message}</p>
          </div>
        )}

        {/* Section 1: Agent Settings */}
        <SettingsSection title="Agent Behavior">

          {/* Agent Sensitivity */}
          <SettingRow
            title="Agent Sensitivity"
            description="How aggressively the agent intervenes when it detects procrastination"
          >
            <div className="flex gap-3">
              {(['low', 'medium', 'high'] as const).map(level => (
                <button
                  key={level}
                  onClick={() => update('agent_sensitivity', level)}
                  className={`px-4 py-2 rounded-lg font-medium capitalize transition ${
                    settings.agent_sensitivity === level
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {level}
                </button>
              ))}
            </div>
            <p className="text-xs text-gray-500 mt-2">
              {settings.agent_sensitivity === 'low'    && 'Agent only intervenes when risk is very high (>80%)'}
              {settings.agent_sensitivity === 'medium' && 'Agent intervenes when risk is moderate (>60%) — recommended'}
              {settings.agent_sensitivity === 'high'   && 'Agent intervenes early and often (>40%) — most aggressive'}
            </p>
          </SettingRow>

          {/* Auto-start sessions */}
          <SettingRow
            title="Auto-Start Sessions"
            description="Agent automatically starts a focus session when it detects you should be studying"
          >
            <Toggle
              value={settings.auto_start_sessions}
              onChange={v => update('auto_start_sessions', v)}
            />
          </SettingRow>

        </SettingsSection>

        {/* Section 2: Session Settings */}
        <SettingsSection title="Session Settings">

          {/* Session duration */}
          <SettingRow
            title="Default Session Duration"
            description="How long each focus session lasts by default"
          >
            <div className="flex items-center gap-3">
              <input
                type="range"
                min={10}
                max={90}
                step={5}
                value={settings.session_duration_mins}
                onChange={e => update('session_duration_mins', Number(e.target.value))}
                className="w-40"
              />
              <span className="font-semibold text-gray-900 w-16">
                {settings.session_duration_mins} min
              </span>
            </div>
          </SettingRow>

          {/* Break duration */}
          <SettingRow
            title="Break Duration"
            description="How long breaks last between sessions"
          >
            <div className="flex items-center gap-3">
              <input
                type="range"
                min={5}
                max={30}
                step={5}
                value={settings.break_duration_mins}
                onChange={e => update('break_duration_mins', Number(e.target.value))}
                className="w-40"
              />
              <span className="font-semibold text-gray-900 w-16">
                {settings.break_duration_mins} min
              </span>
            </div>
          </SettingRow>

          {/* Daily goal */}
          <SettingRow
            title="Daily Focus Goal"
            description="Target focus hours per day"
          >
            <div className="flex items-center gap-3">
              <input
                type="range"
                min={1}
                max={12}
                step={0.5}
                value={settings.daily_goal_hours}
                onChange={e => update('daily_goal_hours', Number(e.target.value))}
                className="w-40"
              />
              <span className="font-semibold text-gray-900 w-16">
                {settings.daily_goal_hours}h
              </span>
            </div>
          </SettingRow>

        </SettingsSection>

        {/* Section 3: Notifications */}
        <SettingsSection title="Notifications">

          {/* Enable notifications */}
          <SettingRow
            title="Enable Notifications"
            description="Allow FocusPilot to send browser notifications"
          >
            <Toggle
              value={settings.notifications_enabled}
              onChange={v => update('notifications_enabled', v)}
            />
          </SettingRow>

          {/* Quiet hours */}
          <SettingRow
            title="Quiet Hours"
            description="No notifications during these hours"
          >
            <div className="flex items-center gap-3">
              <div>
                <label className="text-xs text-gray-500 block mb-1">From</label>
                <select
                  value={settings.quiet_hours_start}
                  onChange={e => update('quiet_hours_start', Number(e.target.value))}
                  className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
                >
                  {Array.from({ length: 24 }, (_, i) => (
                    <option key={i} value={i}>
                      {String(i).padStart(2, '0')}:00
                    </option>
                  ))}
                </select>
              </div>
              <span className="text-gray-500 mt-4">to</span>
              <div>
                <label className="text-xs text-gray-500 block mb-1">Until</label>
                <select
                  value={settings.quiet_hours_end}
                  onChange={e => update('quiet_hours_end', Number(e.target.value))}
                  className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
                >
                  {Array.from({ length: 24 }, (_, i) => (
                    <option key={i} value={i}>
                      {String(i).padStart(2, '0')}:00
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </SettingRow>

        </SettingsSection>

        {/* Section 4: Appearance */}
        <SettingsSection title="Appearance">
          <SettingRow
            title="Theme"
            description="Choose your preferred color theme"
          >
            <div className="flex gap-3">
              {(['light', 'dark', 'system'] as const).map(theme => (
                <button
                  key={theme}
                  onClick={() => update('theme', theme)}
                  className={`px-4 py-2 rounded-lg font-medium capitalize transition ${
                    settings.theme === theme
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {theme}
                </button>
              ))}
            </div>
          </SettingRow>
        </SettingsSection>

        {/* Save button (bottom) */}
        <div className="flex justify-end mt-6">
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-8 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 disabled:bg-gray-400 transition"
          >
            {saving ? 'Saving...' : saved ? 'Saved' : 'Save Changes'}
          </button>
        </div>

      </main>
    </div>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────

function SettingsSection({
  title,
  children
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-white rounded-lg shadow mb-6">
      <div className="px-6 py-4 border-b border-gray-100">
        <h2 className="text-lg font-bold text-gray-900">{title}</h2>
      </div>
      <div className="divide-y divide-gray-100">{children}</div>
    </div>
  );
}

function SettingRow({
  title,
  description,
  children
}: {
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div className="px-6 py-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div className="flex-1">
        <p className="font-semibold text-gray-900">{title}</p>
        <p className="text-sm text-gray-500 mt-0.5">{description}</p>
      </div>
      <div className="flex-shrink-0">{children}</div>
    </div>
  );
}

function Toggle({
  value,
  onChange
}: {
  value: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={value}
      onClick={() => onChange(!value)}
      className={`relative inline-flex h-7 w-14 items-center rounded-full p-0.5 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 ${
        value ? 'bg-blue-600' : 'bg-gray-300'
      }`}
    >
      <span
        className={`inline-block h-6 w-6 rounded-full bg-white shadow transition-transform ${
          value ? 'translate-x-7' : 'translate-x-1'
        }`}
      />
    </button>
  );
}

export default Settings;
