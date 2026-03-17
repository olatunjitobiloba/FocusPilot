// src/types/dna.ts
export interface ClusterProfile {
  cluster_id:      number;
  name:            string;
  n_sessions:      number;
  pct_of_total:    number;
  quality_score:   number;
  color:           string;
  avg_focus_score: number;
  avg_duration:    number;
  avg_distraction: number;
  peak_hour:       number;
  characteristics: string[];
}

export interface DNAInsight {
  type:  'success' | 'info' | 'warning';
  icon:  string;
  title: string;
  body:  string;
}

export interface HeatmapCell {
  hour:     number;
  day:      number;
  day_name: string;
  quality:  number;
  count:    number;
}

export interface DNAResult {
  trained:             boolean;
  n_clusters:          number;
  n_sessions:          number;
  cluster_profiles:    ClusterProfile[];
  peak_hours:          any[];
  best_session_length: any;
  worst_patterns:      any[];
  insights:            DNAInsight[];
  heatmap_data:        HeatmapCell[];
  trained_at:          string;
}
