import React from 'react';
import { useNavigate } from 'react-router-dom';

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-linear-to-br from-green-50 to-emerald-100">
      {/* Navbar */}
      <nav className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <span className="text-2xl font-bold text-green-600">FocusPilot</span>
            </div>
            <div className="flex gap-4">
              <button 
                onClick={() => navigate('/login')}
                className="px-4 py-2 text-green-600 hover:text-green-700"
              >
                Log In
              </button>
              <button 
                onClick={() => navigate('/signup')}
                className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
              >
                Sign Up
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="text-center">
          <h1 className="text-5xl font-bold text-gray-900 mb-6">
            AI Copilot for Your Productivity
          </h1>
          <p className="text-xl text-gray-600 mb-8">
            Put Your Focus on Autopilot
          </p>
          <div className="flex gap-4 justify-center">
            <button 
              onClick={() => navigate('/signup')}
              className="px-8 py-3 bg-green-600 text-white text-lg rounded-lg hover:bg-green-700 shadow-lg"
            >
              Start Free Trial
            </button>
            <button className="px-8 py-3 bg-white text-green-600 text-lg rounded-lg hover:bg-gray-50 shadow-lg border-2 border-green-600">
              Watch Demo
            </button>
          </div>
        </div>

        {/* Features */}
        <div className="mt-20 grid md:grid-cols-3 gap-8">
          <div className="bg-white p-6 rounded-lg shadow-md">
            <h3 className="text-xl font-semibold mb-2">Smart Focus Sessions</h3>
            <p className="text-gray-600">AI-powered work sessions that adapt to your productivity patterns</p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow-md">
            <h3 className="text-xl font-semibold mb-2">Progress Tracking</h3>
            <p className="text-gray-600">Visualize your productivity journey with intelligent analytics</p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow-md">
            <h3 className="text-xl font-semibold mb-2">AI Insights</h3>
            <p className="text-gray-600">Get personalized recommendations to optimize your workflow</p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow-md md:col-span-3">
            <div className="flex items-center gap-3 mb-2">
              <h3 className="text-xl font-semibold">Predicts Procrastination 30 Minutes Before It Happens</h3>
            </div>
            <p className="text-gray-600">FocusPilot's AI analyses your focus patterns in real time and warns you before distraction sets in — so you can stay on track before you even feel the urge to stray.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
