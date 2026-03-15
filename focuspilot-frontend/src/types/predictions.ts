// src/types/predictions.ts
export interface RiskPrediction {
  risk_score:          number;
  risk_percentage:     number;
  risk_level:          'low' | 'medium' | 'high' | 'critical';
  will_procrastinate:  boolean;
  confidence:          'low' | 'medium' | 'high';
  model_available:     boolean;
  top_risk_factors:    RiskFactor[];
  assessed_at:         string;
  message?:            string;
}

export interface RiskFactor {
  factor:   string;
  value:    string;
  severity: 'low' | 'medium' | 'high';
}
