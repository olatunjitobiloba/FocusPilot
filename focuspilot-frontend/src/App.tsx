// src/App.tsx
import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Landing   from './pages/Landing';
import Signup    from './pages/Signup';
import Login     from './pages/Login';
import Dashboard from './pages/Dashboard';
import Blocklist from './pages/Blocklist';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('token');
  if (!token) return <Navigate to="/login" />;
  return <>{children}</>;
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/"          element={<Landing />} />
        <Route path="/signup"    element={<Signup />} />
        <Route path="/login"     element={<Login />} />
        <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/blocklist" element={<ProtectedRoute><Blocklist /></ProtectedRoute>} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
