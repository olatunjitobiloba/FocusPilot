import React from 'react';

export type IconName =
  | 'lock'
  | 'unlock'
  | 'play'
  | 'stop'
  | 'megaphone'
  | 'clock'
  | 'target'
  | 'bolt'
  | 'undo'
  | 'warning'
  | 'shield-check'
  | 'shield-x'
  | 'cpu'
  | 'brain'
  | 'pause'
  | 'activity'
  | 'chart'
  | 'spark'
  | 'bell'
  | 'event'
  | 'cycle'
  | 'recovery'
  | 'intervention'
  | 'search'
  | 'lightbulb'
  | 'medal-gold'
  | 'medal-silver'
  | 'medal-bronze'
  | 'trend-up'
  | 'trend-down'
  | 'check-circle'
  | 'x-circle'
  | 'calendar'
  | 'info';

interface AppIconProps {
  name: IconName;
  className?: string;
  size?: number;
}

function AppIcon({ name, className = '', size = 20 }: AppIconProps) {
  const common = {
    width: size,
    height: size,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 2,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
    className,
    'aria-hidden': true
  };

  switch (name) {
    case 'lock':
      return <svg {...common}><rect x="4" y="11" width="16" height="10" rx="2" /><path d="M8 11V8a4 4 0 1 1 8 0v3" /></svg>;
    case 'unlock':
      return <svg {...common}><rect x="4" y="11" width="16" height="10" rx="2" /><path d="M16 11V8a4 4 0 0 0-8 0" /></svg>;
    case 'play':
      return <svg {...common}><polygon points="8 5 19 12 8 19 8 5" /></svg>;
    case 'stop':
      return <svg {...common}><rect x="7" y="7" width="10" height="10" rx="1" /></svg>;
    case 'megaphone':
      return <svg {...common}><path d="M3 11v2a2 2 0 0 0 2 2h1l2 4h3l-2-4h2l7 3V6l-7 3H5a2 2 0 0 0-2 2z" /></svg>;
    case 'clock':
      return <svg {...common}><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>;
    case 'target':
      return <svg {...common}><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="5" /><circle cx="12" cy="12" r="1.5" /></svg>;
    case 'bolt':
      return <svg {...common}><path d="M13 2L4 14h6l-1 8 9-12h-6l1-8z" /></svg>;
    case 'undo':
      return <svg {...common}><path d="M9 14L4 9l5-5" /><path d="M4 9h9a7 7 0 1 1 0 14h-1" /></svg>;
    case 'warning':
      return <svg {...common}><path d="M12 3L2 21h20L12 3z" /><path d="M12 9v5" /><path d="M12 18h.01" /></svg>;
    case 'shield-check':
      return <svg {...common}><path d="M12 3l8 3v6c0 5-3.5 8.5-8 9-4.5-.5-8-4-8-9V6l8-3z" /><path d="M9 12l2 2 4-4" /></svg>;
    case 'shield-x':
      return <svg {...common}><path d="M12 3l8 3v6c0 5-3.5 8.5-8 9-4.5-.5-8-4-8-9V6l8-3z" /><path d="M10 10l4 4" /><path d="M14 10l-4 4" /></svg>;
    case 'cpu':
      return <svg {...common}><rect x="7" y="7" width="10" height="10" rx="2" /><path d="M9 1v3M15 1v3M9 20v3M15 20v3M1 9h3M1 15h3M20 9h3M20 15h3" /></svg>;
    case 'brain':
      return <svg {...common}><path d="M9.5 4a3.5 3.5 0 0 0-3.5 3.5V9a2.5 2.5 0 0 0 0 5v1a3 3 0 0 0 3 3h1" /><path d="M14.5 4A3.5 3.5 0 0 1 18 7.5V9a2.5 2.5 0 0 1 0 5v1a3 3 0 0 1-3 3h-1" /><path d="M12 4v16" /></svg>;
    case 'pause':
      return <svg {...common}><path d="M9 6v12" /><path d="M15 6v12" /></svg>;
    case 'activity':
      return <svg {...common}><path d="M3 12h4l2-4 4 8 2-4h6" /></svg>;
    case 'chart':
      return <svg {...common}><path d="M4 20V6" /><path d="M10 20V10" /><path d="M16 20V4" /><path d="M22 20H2" /></svg>;
    case 'spark':
      return <svg {...common}><path d="M12 3l1.8 4.2L18 9l-4.2 1.8L12 15l-1.8-4.2L6 9l4.2-1.8L12 3z" /></svg>;
    case 'bell':
      return <svg {...common}><path d="M18 16V11a6 6 0 1 0-12 0v5l-2 2h16l-2-2z" /><path d="M10 20a2 2 0 0 0 4 0" /></svg>;
    case 'event':
      return <svg {...common}><circle cx="12" cy="12" r="9" /><path d="M8 12h8" /></svg>;
    case 'cycle':
      return <svg {...common}><path d="M4 12a8 8 0 0 1 14-5" /><path d="M18 4v4h-4" /><path d="M20 12a8 8 0 0 1-14 5" /><path d="M6 20v-4h4" /></svg>;
    case 'recovery':
      return <svg {...common}><path d="M20 6L9 17l-5-5" /></svg>;
    case 'intervention':
      return <svg {...common}><path d="M12 2v8" /><path d="M7 6l10 12" /><path d="M17 6L7 18" /></svg>;
    case 'search':
      return <svg {...common}><circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /></svg>;
    case 'lightbulb':
      return <svg {...common}><path d="M9 18h6" /><path d="M10 22h4" /><path d="M12 2a7 7 0 0 0-4 12c1 1 1 2 1 4h6c0-2 0-3 1-4a7 7 0 0 0-4-12z" /></svg>;
    case 'medal-gold':
      return <svg {...common}><circle cx="12" cy="9" r="4" /><path d="M9 13l-2 8 5-3 5 3-2-8" /></svg>;
    case 'medal-silver':
      return <svg {...common}><circle cx="12" cy="9" r="4" /><path d="M9 13l-2 8 5-3 5 3-2-8" /></svg>;
    case 'medal-bronze':
      return <svg {...common}><circle cx="12" cy="9" r="4" /><path d="M9 13l-2 8 5-3 5 3-2-8" /></svg>;
    case 'trend-up':
      return <svg {...common}><path d="M3 17l6-6 4 4 7-7" /><path d="M14 8h6v6" /></svg>;
    case 'trend-down':
      return <svg {...common}><path d="M3 7l6 6 4-4 7 7" /><path d="M14 16h6v-6" /></svg>;
    case 'check-circle':
      return <svg {...common}><circle cx="12" cy="12" r="9" /><path d="M8 12l2.5 2.5L16 9" /></svg>;
    case 'x-circle':
      return <svg {...common}><circle cx="12" cy="12" r="9" /><path d="M9 9l6 6" /><path d="M15 9l-6 6" /></svg>;
    case 'calendar':
      return <svg {...common}><rect x="4" y="5" width="16" height="15" rx="2" /><path d="M8 3v4M16 3v4M4 10h16" /></svg>;
    case 'info':
      return <svg {...common}><circle cx="12" cy="12" r="9" /><path d="M12 10v6" /><path d="M12 7h.01" /></svg>;
    default:
      return <svg {...common}><circle cx="12" cy="12" r="9" /></svg>;
  }
}

export default AppIcon;
