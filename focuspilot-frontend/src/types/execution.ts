// src/types/execution.ts
export interface AgentAction {
  id:                    string;
  action_type:           string;
  action_data:           Record<string, any>;
  trigger_reason:        string;
  risk_score_at_trigger: number;
  status:                'pending' | 'executing' | 'completed' | 'failed' | 'undone';
  is_undoable:           boolean;
  result:                Record<string, any>;
  created_at:            string;
  completed_at:          string | null;
  undone_at:             string | null;
}

export interface BlockState {
  is_blocked:      boolean;
  blocked_domains: string[];
  blocked_at:      string | null;
  unblock_at:      string | null;
  block_reason:    string | null;
}
