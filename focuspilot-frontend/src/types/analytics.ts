// src/types/analytics.ts
export interface AnalyticsSummary {
  total_sessions:         number;
  total_focused_hours:    number;
  avg_focus_score:        number;
  avg_session_duration:   number;
  total_distraction_mins: number;
  completion_rate:        number;
}

export interface DailyBreakdown {
  date:        string;
  day_label:   string;
  day_short:   string;
  sessions:    number;
  avg_score:   number;
  total_mins:  number;
  total_hours: number;
  has_session: boolean;
}

export interface SessionRow {
  id:            string;
  date:          string;
  day:           string;
  start_time:    string;
  end_time:      string;
  duration_mins: number;
  focus_score:   number | null;
  planned_mins:  number | null;
  auto_started:  boolean;
}

export interface WeeklyReport {
  week_label:      string;
  this_week:       AnalyticsSummary;
  last_week:       any;
  improvement:     any;
  achievements:    any[];
  improvements:    any[];
  recommendations: string[];
  streak:          any;
  best_day:        any;
  best_hour:       any;
}
