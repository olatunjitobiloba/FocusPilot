// src/mocks/handlers.ts
import { http, HttpResponse } from 'msw';

const API_URL = 'https://olatunjitobi-focuspilot-agent.hf.space';

export const handlers = [

  // Auth
  http.post(`${API_URL}/auth/login`, () => {
    return HttpResponse.json({
      access_token: 'mock-token-12345',
      token_type:   'bearer',
      user: {
        id:        'user-123',
        email:     'test@test.com',
        full_name: 'Test User'
      }
    });
  }),

  http.post(`${API_URL}/auth/signup`, () => {
    return HttpResponse.json({
      access_token: 'mock-token-12345',
      token_type:   'bearer',
      user: {
        id:        'user-123',
        email:     'test@test.com',
        full_name: 'Test User'
      }
    });
  }),

  http.get(`${API_URL}/auth/me`, () => {
    return HttpResponse.json({
      id:        'user-123',
      email:     'test@test.com',
      full_name: 'Test User'
    });
  }),

  // Stats
  http.get(`${API_URL}/stats/daily`, () => {
    return HttpResponse.json({
      date:               '2024-01-15',
      focus_hours:        3.5,
      sessions_completed: 4,
      avg_focus_score:    7.5,
      streak:             5
    });
  }),

  http.get(`${API_URL}/stats/weekly`, () => {
    return HttpResponse.json({
      period:          '7_days',
      total_hours:     18.5,
      avg_daily_hours: 2.6,
      total_sessions:  22,
      daily_breakdown: {
        '2024-01-09': { minutes: 120, sessions: 2 },
        '2024-01-10': { minutes: 150, sessions: 3 },
        '2024-01-11': { minutes: 90,  sessions: 2 },
        '2024-01-12': { minutes: 180, sessions: 3 },
        '2024-01-13': { minutes: 60,  sessions: 1 },
        '2024-01-14': { minutes: 200, sessions: 4 },
        '2024-01-15': { minutes: 110, sessions: 2 },
      }
    });
  }),

  // Sessions
  http.get(`${API_URL}/sessions/active`, () => {
    return HttpResponse.json({ active: false });
  }),

  http.post(`${API_URL}/sessions/start`, () => {
    return HttpResponse.json({
      session_id: 'session-456',
      start_time: new Date().toISOString(),
      message:    'Session started'
    });
  }),

  http.get(`${API_URL}/sessions/summary`, () => {
    return HttpResponse.json({
      total_sessions:       22,
      total_hours:          18.5,
      avg_session_minutes:  50,
      avg_focus_score:      7.2,
      longest_session_minutes: 90,
      total_distractions:   45
    });
  }),

  // Recommendations
  http.get(`${API_URL}/recommendations/`, () => {
    return HttpResponse.json({
      recommendations: [
        {
          type:     'best_time',
          title:    'Your Peak Hour',
          message:  'You focus best at 09:00. Schedule important tasks then!',
          priority: 'medium'
        }
      ],
      total: 1
    });
  }),

  // Blocklist
  http.get(`${API_URL}/blocklist/`, () => {
    return HttpResponse.json({
      blocklist: [
        {
          id:       'block-1',
          domain:   'youtube.com',
          reason:   'Too distracting',
          added_at: '2024-01-10T10:00:00Z'
        }
      ]
    });
  }),

  http.post(`${API_URL}/blocklist/`, () => {
    return HttpResponse.json({
      message: 'Added to blocklist',
      item:    { domain: 'instagram.com' }
    });
  }),

  http.delete(`${API_URL}/blocklist/:domain`, () => {
    return HttpResponse.json({ message: 'Removed from blocklist' });
  }),

  // Suggestions
  http.get(`${API_URL}/suggestions/`, () => {
    return HttpResponse.json({
      suggestions: [
        {
          domain:            'instagram.com',
          distraction_score: 72.5,
          confidence:        'high',
          reason:            'You visit instagram.com during 80% of low-focus sessions.',
          total_visits:      15,
          total_minutes:     45.2,
          factors: {
            low_focus_ratio:   0.8,
            time_score:        0.6,
            abandonment_ratio: 0.4,
            timing_score:      0.5
          }
        }
      ],
      already_blocked: [],
      data_points:     156
    });
  }),

  http.post(`${API_URL}/suggestions/accept`, () => {
    return HttpResponse.json({
      message: '✅ instagram.com added to blocklist',
      action:  'blocked'
    });
  }),

  http.post(`${API_URL}/suggestions/dismiss`, () => {
    return HttpResponse.json({
      message: 'Suggestion dismissed',
      action:  'dismissed'
    });
  }),
];
