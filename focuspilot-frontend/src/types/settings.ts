// src/types/settings.ts
export interface UserSettings {
  notifications_enabled:  boolean;
  agent_sensitivity:      'low' | 'medium' | 'high';
  auto_start_sessions:    boolean;
  session_duration_mins:  number;
  break_duration_mins:    number;
  daily_goal_hours:       number;
  quiet_hours_start:      number;  // 0-23
  quiet_hours_end:        number;  // 0-23
  theme:                  'light' | 'dark' | 'system';
}

export const DEFAULT_SETTINGS: UserSettings = {
  notifications_enabled: true,
  agent_sensitivity:     'medium',
  auto_start_sessions:   false,
  session_duration_mins: 25,
  break_duration_mins:   5,
  daily_goal_hours:      4,
  quiet_hours_start:     22,
  quiet_hours_end:       8,
  theme:                 'system'
};
