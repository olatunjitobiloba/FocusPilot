// src/App.tsx
import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Landing   from './pages/Landing';
import Signup    from './pages/Signup';
import Login     from './pages/Login';
import Dashboard from './pages/Dashboard';
import AgentStatus from './pages/AgentStatus';
import AgentDashboard from './pages/AgentDashboard';
import Blocklist from './pages/Blocklist';
import Settings  from './pages/Settings';
import ExecutionLog from './pages/ExecutionLog';
import ProductivityDNA from './pages/ProductivityDNA';
import Analytics from './pages/Analytics';
import { applyTheme, getStoredTheme } from './utils/theme';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('token');
  if (!token) return <Navigate to="/login" />;
  return <>{children}</>;
}

function App() {
  useEffect(() => {
    applyTheme(getStoredTheme());
  }, []);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/"          element={<Landing />} />
        <Route path="/signup"    element={<Signup />} />
        <Route path="/login"     element={<Login />} />
        <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route
          path="/agent"
          element={
            <ProtectedRoute>
              <AgentStatus />
            </ProtectedRoute>
          }
        />
        <Route
          path="/agent-dashboard"
          element={
            <ProtectedRoute>
              <AgentDashboard />
            </ProtectedRoute>
          }
        />
        <Route path="/blocklist" element={<ProtectedRoute><Blocklist /></ProtectedRoute>} />
        <Route
          path="/settings"
          element={
            <ProtectedRoute>
              <Settings />
            </ProtectedRoute>
          }
        />
        <Route
          path="/execution"
          element={
            <ProtectedRoute>
              <ExecutionLog />
            </ProtectedRoute>
          }
        />
        <Route
          path="/dna"
          element={
            <ProtectedRoute>
              <ProductivityDNA />
            </ProtectedRoute>
          }
        />
        <Route
          path="/analytics"
          element={
            <ProtectedRoute>
              <Analytics />
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
