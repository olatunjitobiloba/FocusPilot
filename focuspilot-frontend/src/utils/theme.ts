export type ThemeMode = 'light' | 'dark' | 'system';

const THEME_STORAGE_KEY = 'focuspilot-theme';

function resolveSystemTheme(): 'light' | 'dark' {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
    return 'light';
  }

  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

export function applyTheme(theme: ThemeMode): 'light' | 'dark' {
  const resolvedTheme = theme === 'system' ? resolveSystemTheme() : theme;
  const root = document.documentElement;

  root.setAttribute('data-theme', resolvedTheme);
  root.classList.toggle('theme-dark', resolvedTheme === 'dark');
  root.classList.toggle('theme-light', resolvedTheme === 'light');

  return resolvedTheme;
}

export function getStoredTheme(): ThemeMode {
  const storedTheme = localStorage.getItem(THEME_STORAGE_KEY);
  if (storedTheme === 'light' || storedTheme === 'dark' || storedTheme === 'system') {
    return storedTheme;
  }
  return 'system';
}

export function storeTheme(theme: ThemeMode): void {
  localStorage.setItem(THEME_STORAGE_KEY, theme);
}
