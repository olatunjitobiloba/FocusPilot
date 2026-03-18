// src/types/rl.ts
export interface RLEpisode {
  id:              string;
  session_id:      string;
  state_key:       string;
  action:          string;
  reward:          number | null;
  outcome:         string | null;
  q_value_before:  number | null;
  q_value_after:   number | null;
  next_state_key:  string | null;
  created_at:      string;
}

export interface LearningStats {
  total_episodes:   number;
  avg_reward:       number;
  success_rate:     number;
  most_used_action: string;
  action_counts:    Record<string, number>;
  reward_trend:     { episode: number; avg_reward: number }[];
}

export interface PolicyEntry {
  state_key:   string;
  best_action: string;
  best_q:      number;
  visit_count: number;
  all_actions: Record<string, number>;
}
