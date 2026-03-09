// src/api/client.ts
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || "https://OlatunjiTobi-focuspilot-agent.hf.space";

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
export const authAPI = {
  signup: (email: string, password: string, fullName: string) =>
    api.post('/auth/signup', { email, password, full_name: fullName }),
  
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),
  
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
