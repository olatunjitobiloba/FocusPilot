-- ==============================================================================
-- FocusPilot Complete Database Schema (Supabase / PostgreSQL)
-- Reconstructed from backend models, route handlers, and ML engines
-- ==============================================================================

-- 1. Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ==============================================================================
-- Core Authentication & Users
-- ==============================================================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE UNIQUE NOT NULL,
    settings JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==============================================================================
-- Focus Sessions & Browsing Activity
-- ==============================================================================
CREATE TABLE IF NOT EXISTS focus_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    start_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    end_time TIMESTAMPTZ,
    duration_minutes INTEGER,
    focus_score INTEGER,
    distraction_count INTEGER DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_focus_sessions_user_time ON focus_sessions(user_id, start_time DESC);
CREATE UNIQUE INDEX IF NOT EXISTS unique_active_session_per_user ON focus_sessions (user_id) WHERE end_time IS NULL;

CREATE TABLE IF NOT EXISTS browsing_activity (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES focus_sessions(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    url TEXT NOT NULL,
    domain TEXT NOT NULL,
    duration_seconds INTEGER DEFAULT 0,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_browsing_activity_user_time ON browsing_activity(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_browsing_activity_session ON browsing_activity(session_id);

-- ==============================================================================
-- Website Blocking & Domain Rules
-- ==============================================================================
CREATE TABLE IF NOT EXISTS blocklist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    domain TEXT NOT NULL,
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (user_id, domain)
);

CREATE TABLE IF NOT EXISTS site_block_state (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    is_blocked BOOLEAN DEFAULT FALSE,
    blocked_domains JSONB DEFAULT '[]'::jsonb,
    blocked_at TIMESTAMPTZ,
    unblock_at TIMESTAMPTZ,
    block_reason TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS suggestion_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    domain TEXT NOT NULL,
    action TEXT NOT NULL, -- e.g. 'productive', 'dismissed'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (user_id, domain, action)
);

-- ==============================================================================
-- Autonomous Agent & Real-Time Intervention State
-- ==============================================================================
CREATE TABLE IF NOT EXISTS agent_state (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    state TEXT DEFAULT 'idle',
    risk_score NUMERIC DEFAULT 0.0,
    last_cycle TIMESTAMPTZ,
    cycle_count INTEGER DEFAULT 0,
    last_action TEXT,
    last_assessed TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agent_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    action_type TEXT NOT NULL,
    action_data JSONB DEFAULT '{}'::jsonb,
    trigger_reason TEXT,
    risk_score_at_trigger NUMERIC,
    status TEXT DEFAULT 'executing',
    is_undoable BOOLEAN DEFAULT FALSE,
    result JSONB,
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    undone_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS agent_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    event_type TEXT NOT NULL,
    event_data JSONB DEFAULT '{}'::jsonb,
    risk_level TEXT,
    risk_score NUMERIC,
    signals JSONB,
    state_before TEXT,
    cycle INTEGER,
    actions JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agent_interventions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    intervention_type TEXT NOT NULL,
    trigger_reason TEXT,
    risk_score_at_trigger NUMERIC,
    outcome TEXT,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS intervention_outcomes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    intervention_type TEXT NOT NULL,
    risk_score_before NUMERIC,
    risk_score_after NUMERIC,
    outcome TEXT,
    time_to_refocus_mins NUMERIC,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notification_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    type TEXT NOT NULL,
    read BOOLEAN DEFAULT FALSE,
    extra_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS scheduled_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    action_type TEXT NOT NULL,
    action_data JSONB DEFAULT '{}'::jsonb,
    domains JSONB,
    scheduled_for TIMESTAMPTZ NOT NULL,
    status TEXT DEFAULT 'pending',
    executed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS risk_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    risk_score NUMERIC NOT NULL,
    assessed_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_risk_history_user_time ON risk_history(user_id, assessed_at DESC);

CREATE TABLE IF NOT EXISTS user_behavior_profile (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    best_intervention TEXT,
    worst_intervention TEXT,
    total_interventions INTEGER DEFAULT 0,
    successful_interventions INTEGER DEFAULT 0,
    preferred_message_tone TEXT DEFAULT 'neutral',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==============================================================================
-- ML DNA Clustering (Behavioral Fingerprinting)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS productivity_clusters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE UNIQUE NOT NULL,
    n_clusters INTEGER,
    cluster_profiles JSONB,
    session_assignments JSONB,
    peak_hours JSONB,
    best_session_length TEXT,
    worst_patterns JSONB,
    insights JSONB,
    heatmap_data JSONB,
    trained_at TIMESTAMPTZ DEFAULT NOW(),
    sessions_analyzed INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS session_clusters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    session_id UUID REFERENCES focus_sessions(id) ON DELETE CASCADE NOT NULL,
    cluster_label INTEGER NOT NULL,
    cluster_name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (user_id, session_id)
);

-- ==============================================================================
-- Reinforcement Learning (Q-Learning Engine)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS rl_episodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    session_id TEXT,
    state_key TEXT NOT NULL,
    action TEXT NOT NULL,
    q_value_before DOUBLE PRECISION,
    q_value_after DOUBLE PRECISION,
    reward DOUBLE PRECISION,
    outcome TEXT,
    next_state_key TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS q_table (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    state_key TEXT NOT NULL,
    action TEXT NOT NULL,
    q_value DOUBLE PRECISION DEFAULT 0.0,
    visit_count INTEGER DEFAULT 1,
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (user_id, state_key, action)
);

-- Stored Procedure called by Q-learning agent to increment state visits atomically
CREATE OR REPLACE FUNCTION increment_visit_count(
    p_user_id UUID,
    p_state_key TEXT,
    p_action TEXT
)
RETURNS VOID AS $$
BEGIN
    UPDATE q_table
    SET visit_count = COALESCE(visit_count, 0) + 1,
        last_updated = NOW()
    WHERE user_id = p_user_id
      AND state_key = p_state_key
      AND action = p_action;
END;
$$ LANGUAGE plpgsql;

-- ==============================================================================
-- Row Level Security (RLS) Configuration
-- ==============================================================================
-- Disable RLS by default so your FastAPI backend (using service/anon key)
-- has unobstructed access across all endpoints.
ALTER TABLE users DISABLE ROW LEVEL SECURITY;
ALTER TABLE user_settings DISABLE ROW LEVEL SECURITY;
ALTER TABLE focus_sessions DISABLE ROW LEVEL SECURITY;
ALTER TABLE browsing_activity DISABLE ROW LEVEL SECURITY;
ALTER TABLE blocklist DISABLE ROW LEVEL SECURITY;
ALTER TABLE site_block_state DISABLE ROW LEVEL SECURITY;
ALTER TABLE suggestion_feedback DISABLE ROW LEVEL SECURITY;
ALTER TABLE agent_state DISABLE ROW LEVEL SECURITY;
ALTER TABLE agent_actions DISABLE ROW LEVEL SECURITY;
ALTER TABLE agent_events DISABLE ROW LEVEL SECURITY;
ALTER TABLE agent_interventions DISABLE ROW LEVEL SECURITY;
ALTER TABLE intervention_outcomes DISABLE ROW LEVEL SECURITY;
ALTER TABLE notification_queue DISABLE ROW LEVEL SECURITY;
ALTER TABLE scheduled_actions DISABLE ROW LEVEL SECURITY;
ALTER TABLE risk_history DISABLE ROW LEVEL SECURITY;
ALTER TABLE user_behavior_profile DISABLE ROW LEVEL SECURITY;
ALTER TABLE productivity_clusters DISABLE ROW LEVEL SECURITY;
ALTER TABLE session_clusters DISABLE ROW LEVEL SECURITY;
ALTER TABLE rl_episodes DISABLE ROW LEVEL SECURITY;
ALTER TABLE q_table DISABLE ROW LEVEL SECURITY;

