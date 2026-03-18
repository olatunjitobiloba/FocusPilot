// src/api/client.ts
import axios from 'axios';
import type { UserSettings } from '../types/settings';

const API_URL = process.env.REACT_APP_API_URL || "https://OlatunjiTobi-focuspilot-agent.hf.space";

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

let refreshPromise: Promise<string | null> | null = null;

const refreshAccessToken = async (): Promise<string | null> => {
  const refreshToken = localStorage.getItem('refresh_token');
  if (!refreshToken) return null;

  if (!refreshPromise) {
    refreshPromise = axios
      .post(`${API_URL}/auth/refresh`, { refresh_token: refreshToken }, {
        headers: {
          'Content-Type': 'application/json',
        },
      })
      .then((response) => {
        const newAccessToken = response.data?.access_token;
        const newRefreshToken = response.data?.refresh_token;
        const user = response.data?.user;

        if (!newAccessToken) return null;

        localStorage.setItem('token', newAccessToken);
        if (newRefreshToken) {
          localStorage.setItem('refresh_token', newRefreshToken);
        }
        if (user) {
          localStorage.setItem('user', JSON.stringify(user));
        }

        window.postMessage(
          {
            source: 'focuspilot-web',
            action: 'syncToken',
            token: newAccessToken,
            refreshToken: newRefreshToken,
            user,
            apiUrl: API_URL,
          },
          '*'
        );

        return newAccessToken;
      })
      .catch(() => null)
      .finally(() => {
        refreshPromise = null;
      });
  }

  return refreshPromise;
};

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config || {};
    const status = error.response?.status;

    if ((status === 401 || status === 403) && !originalRequest._retry && !String(originalRequest.url || '').includes('/auth/refresh')) {
      originalRequest._retry = true;

      const newAccessToken = await refreshAccessToken();
      if (newAccessToken) {
        originalRequest.headers = originalRequest.headers || {};
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        return api(originalRequest);
      }

      localStorage.clear();

      const currentPath = window.location.pathname;
      if (!['/login', '/signup', '/'].includes(currentPath)) {
        window.location.href = '/login';
      }
    }

    return Promise.reject(error);
  }
);

export const authAPI = {
  signup: (email: string, password: string, fullName: string) =>
    api.post('/auth/signup', { email, password, full_name: fullName }),
  
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),

  refresh: (refreshToken: string) =>
    api.post('/auth/refresh', { refresh_token: refreshToken }),
  
  me: () => api.get('/auth/me'),
};

export const blocklistAPI = {
  getAll: () =>
    api.get('/blocklist/'),

  add: (domain: string, reason?: string) =>
    api.post('/blocklist/', { domain, reason }),

  remove: (domain: string) =>
    api.delete(`/blocklist/${domain}`),
};

export const suggestionsAPI = {
  getAll: () =>
    api.get('/suggestions/'),

  accept: (domain: string) =>
    api.post('/suggestions/accept', { domain }),

  dismiss: (domain: string) =>
    api.post('/suggestions/dismiss', { domain }),

  score: (domain: string) =>
    api.get(`/suggestions/score/${domain}`),
};

export const whitelistAPI = {
  getAll: () =>
    api.get('/whitelist/'),

  add: (domain: string) =>
    api.post('/whitelist/', { domain }),

  remove: (domain: string) =>
    api.delete(`/whitelist/${domain}`),
};

export const settingsAPI = {
  get: () =>
    api.get('/settings/'),

  update: (settings: Partial<UserSettings>) =>
    api.put('/settings/', settings),

  getDataStatus: () =>
    api.get('/ml/data-status'),
};

export const predictionsAPI = {
  getRisk: () =>
    api.get('/predictions/risk'),

  getModelStatus: () =>
    api.get('/predictions/model-status'),

  trainModel: () =>
    api.post('/predictions/train'),

  getFeatureImportance: () =>
    api.get('/predictions/feature-importance'),

  getRiskHistory: () =>
    api.get('/predictions/risk/history'),
};

export const agentAPI = {
  getStatus: () =>
    api.get('/agent/status'),

  triggerCycle: () =>
    api.post('/agent/cycle'),

  pause: () =>
    api.post('/agent/pause'),

  resume: () =>
    api.post('/agent/resume'),

  getEvents: (limit = 20) =>
    api.get(`/agent/events?limit=${limit}`),

  getInterventions: (limit = 20) =>
    api.get(`/agent/interventions?limit=${limit}`),

  getNotifications: (limit = 50) =>
    api.get(`/agent/notifications?limit=${limit}`),

  markNotificationsRead: () =>
    api.post('/agent/notifications/mark-read'),
};

export const executionAPI = {
  getActions: (limit = 20) =>
    api.get(`/execution/actions?limit=${limit}`),

  getUndoable: () =>
    api.get('/execution/undoable'),

  undoAction: (id: string) =>
    api.post(`/execution/undo/${id}`),

  getBlockState: () =>
    api.get('/execution/block-state'),

  manualBlock: (minutes: number) =>
    api.post('/execution/block', { duration_minutes: minutes }),

  manualUnblock: () =>
    api.post('/execution/unblock'),

  sendNudge: (title: string, message: string) =>
    api.post('/execution/nudge', { title, message }),
};

export const pipelineAPI = {
  getHealth: () =>
    api.get('/pipeline/health'),

  getSummary: () =>
    api.get('/pipeline/summary'),

  runNow: () =>
    api.post('/pipeline/run'),
};

export const analyticsAPI = {
  getOverview: (days = 30) =>
    api.get(`/analytics/overview?days=${days}`),

  getSummary: (days = 7) =>
    api.get(`/analytics/summary?days=${days}`),

  getTrends: (days = 30) =>
    api.get(`/analytics/trends?days=${days}`),

  getTimeBreakdown: (days = 30) =>
    api.get(`/analytics/time-breakdown?days=${days}`),

  getSessions: (days = 30) =>
    api.get(`/analytics/sessions?days=${days}`),

  getWeeklyReport: () =>
    api.get('/analytics/weekly-report'),

  getAgentStats: (days = 30) =>
    api.get(`/analytics/agent-stats?days=${days}`),
};

export const dnaAPI = {
  train: () =>
    api.post('/dna/train/sync', {}, { timeout: 120000 }),

  getResults: () =>
    api.get('/dna/results'),

  getInsights: () =>
    api.get('/dna/insights'),

  getClusters: () =>
    api.get('/dna/clusters'),

  getEligibility: () =>
    api.get('/dna/eligibility'),
};
