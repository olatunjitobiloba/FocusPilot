export const GREEN_SCALE = {
  50: '#f0fdf4',
  100: '#dcfce7',
  200: '#bbf7d0',
  300: '#86efac',
  400: '#4ade80',
  500: '#22c55e',
  600: '#16a34a',
  700: '#15803d',
  800: '#166534',
  900: '#14532d'
} as const;

export const CHART_GREEN = {
  bar: GREEN_SCALE[600],
  line: GREEN_SCALE[700],
  dot: GREEN_SCALE[700],
  series: [
    GREEN_SCALE[300],
    GREEN_SCALE[400],
    GREEN_SCALE[500],
    GREEN_SCALE[600],
    GREEN_SCALE[700]
  ],
  heatmap: [
    GREEN_SCALE[200],
    GREEN_SCALE[400],
    GREEN_SCALE[700],
    GREEN_SCALE[800]
  ]
} as const;

export const BADGE_GREEN = {
  bg: 'bg-green-100',
  text: 'text-green-700',
  accent: 'text-green-600',
  accentStrong: 'text-green-700'
} as const;

export const ALERT_TONES = {
  warning: '#eab308',
  critical: '#ef4444'
} as const;
