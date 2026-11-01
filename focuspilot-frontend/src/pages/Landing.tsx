import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

export default function Landing() {
  const navigate = useNavigate();

  // Interactive Live Simulator State
  const [activeTab, setActiveTab] = useState<'deep' | 'sprint' | 'break'>('deep');
  const [isDemoRunning, setIsDemoRunning] = useState(true);
  const [demoSeconds, setDemoSeconds] = useState(1458); // 24m 18s
  const [riskScore, setRiskScore] = useState(14);

  // Dynamic durations based on selected tab
  const tabDurations = {
    deep: 25 * 60,
    sprint: 50 * 60,
    break: 5 * 60,
  };

  const currentMax = tabDurations[activeTab];

  // Simulator timer effect
  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (isDemoRunning) {
      timer = setInterval(() => {
        setDemoSeconds((prev) => {
          if (prev <= 1) return currentMax;
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [isDemoRunning, currentMax]);

  const switchTab = (tab: 'deep' | 'sprint' | 'break') => {
    setActiveTab(tab);
    if (tab === 'deep') {
      setDemoSeconds(24 * 60 + 18);
      setRiskScore(14);
    } else if (tab === 'sprint') {
      setDemoSeconds(47 * 60 + 40);
      setRiskScore(22);
    } else {
      setDemoSeconds(4 * 60 + 35);
      setRiskScore(5);
    }
  };

  // Radial progress calculations
  const progressPercent = Math.min(100, Math.max(0, ((currentMax - demoSeconds) / currentMax) * 100));
  const radius = 76;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (progressPercent / 100) * circumference;

  const formatTimer = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div className="min-h-screen bg-[#07090E] text-slate-100 selection:bg-emerald-500/30 selection:text-emerald-200 relative overflow-x-hidden font-sans">
      {/* Ambient Radial Mesh Illumination */}
      <div className="pointer-events-none fixed inset-0 z-0">
        <div className="absolute -top-32 left-1/2 -translate-x-1/2 w-[700px] sm:w-[1000px] h-[550px] bg-gradient-to-b from-emerald-500/15 via-teal-500/5 to-transparent rounded-full blur-3xl opacity-75" />
        <div className="absolute top-[35%] -left-48 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl opacity-50" />
        <div className="absolute top-[60%] -right-48 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl opacity-40" />
        <div className="absolute inset-0 bg-[radial-gradient(#ffffff08_1px,transparent_1px)] [background-size:24px_24px] opacity-60" />
      </div>

      {/* Floating Island Navigation (Dribbble Glass Pill) */}
      <header className="sticky top-5 z-50 px-4 sm:px-6">
        <nav className="max-w-5xl mx-auto rounded-full bg-slate-900/80 border border-white/10 backdrop-blur-xl shadow-2xl px-5 sm:px-7 py-3 flex items-center justify-between transition-all duration-300 hover:border-white/15">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/')}
              className="flex items-center gap-2.5 text-left group"
            >
              <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 group-hover:scale-105 transition-transform duration-200 shadow-xs shadow-emerald-500/20">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <span className="text-lg font-bold tracking-tight text-white group-hover:text-emerald-300 transition-colors">
                FocusPilot
              </span>
            </button>
            <span className="hidden md:inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-medium bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              OS v2.4
            </span>
          </div>

          <div className="hidden lg:flex items-center gap-7 text-sm font-medium text-slate-300">
            <a href="#simulator" className="hover:text-white transition-colors">Live HUD</a>
            <a href="#features" className="hover:text-white transition-colors">Architecture</a>
            <a href="#why-focuspilot" className="hover:text-white transition-colors">Why FocusPilot</a>
            <a href="#extension" className="hover:text-white transition-colors">Chrome Extension</a>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/login')}
              className="text-sm font-semibold text-slate-300 hover:text-white px-3 py-1.5 transition"
            >
              Sign In
            </button>
            <button
              onClick={() => navigate('/signup')}
              className="relative group overflow-hidden rounded-full px-5 py-2 text-xs sm:text-sm font-bold bg-emerald-400 text-slate-950 hover:bg-emerald-300 transition shadow-lg shadow-emerald-500/20 active:scale-95 flex items-center gap-1.5"
            >
              <span>Get Started</span>
              <span className="w-4 h-4 rounded-full bg-slate-950/15 flex items-center justify-center text-[10px] group-hover:translate-x-0.5 transition-transform">
                ↗
              </span>
            </button>
          </div>
        </nav>
      </header>

      {/* Main Content */}
      <main className="relative z-10 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pt-14 sm:pt-20 pb-28">
        
        {/* HERO SECTION */}
        <section className="text-center max-w-4xl mx-auto mb-16 sm:mb-24">
          {/* Eyebrow Pill */}
          <div className="inline-flex items-center gap-2.5 px-3.5 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs font-semibold uppercase tracking-[0.18em] mb-6 sm:mb-8 shadow-xs">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400" />
            </span>
            AI-Powered Behavioral Productivity OS
          </div>

          {/* Master Heading */}
          <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-white leading-[1.08] mb-6 sm:mb-8">
            Stop fighting distraction. <br className="hidden sm:block" />
            Let AI protect your{' '}
            <span className="text-emerald-300">
              flow state.
            </span>
          </h1>

          {/* Subtitle */}
          <p className="text-base sm:text-lg lg:text-xl text-slate-300 max-w-2xl mx-auto leading-relaxed mb-8 sm:mb-10 font-normal">
            Most blockers treat everyone the same. FocusPilot learns your behavioral fingerprint—predicting procrastination in real-time, blocking distraction adaptively, and preserving deep cognitive momentum.
          </p>

          {/* Action CTAs */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 max-w-md mx-auto mb-12">
            <button
              onClick={() => navigate('/signup')}
              className="w-full sm:w-auto px-8 py-3.5 rounded-full bg-emerald-400 text-slate-950 font-bold hover:bg-emerald-300 transition duration-200 shadow-xl shadow-emerald-500/20 active:scale-95 flex items-center justify-center gap-2 text-base"
            >
              <span>Launch Autonomous OS</span>
              <span className="w-5 h-5 rounded-full bg-slate-950/15 flex items-center justify-center text-xs">
                ↗
              </span>
            </button>
            <a
              href="#simulator"
              className="w-full sm:w-auto px-6 py-3.5 rounded-full border border-white/15 bg-white/5 hover:bg-white/10 text-white font-medium transition text-base backdrop-blur-sm flex items-center justify-center gap-2"
            >
              <svg className="w-4 h-4 text-emerald-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
              </svg>
              <span>Try Live Simulator</span>
            </a>
          </div>

          {/* Micro Telemetry Badges */}
          <div className="flex flex-wrap items-center justify-center gap-6 sm:gap-10 text-xs font-medium text-slate-400 border-t border-white/10 pt-8 max-w-2xl mx-auto">
            <div className="flex items-center gap-2">
              <span className="text-emerald-400 font-bold">⚡ 0ms</span> Extension Latency
            </div>
            <div className="flex items-center gap-2">
              <span className="text-emerald-400 font-bold">🧠 4-Factor</span> ML Distraction Model
            </div>
            <div className="flex items-center gap-2">
              <span className="text-emerald-400 font-bold">🛡️ 100%</span> Client-Side Privacy
            </div>
          </div>
        </section>

        {/* CENTERPIECE: INTERACTIVE DRIBBLE HUD & 21ST.DEV RADIAL TIMER SIMULATOR */}
        <section id="simulator" className="mb-28 scroll-mt-28">
          <div className="relative rounded-3xl p-1 bg-gradient-to-b from-emerald-500/30 via-white/10 to-transparent shadow-[0_0_60px_rgba(16,185,129,0.15)]">
            <div className="rounded-[22px] bg-[#0C111C] border border-white/10 overflow-hidden backdrop-blur-2xl">
              
              {/* Window Header Shell */}
              <div className="px-5 sm:px-7 py-4 bg-slate-900/90 border-b border-white/10 flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-rose-500/80" />
                  <span className="w-3 h-3 rounded-full bg-amber-500/80" />
                  <span className="w-3 h-3 rounded-full bg-emerald-500/80" />
                  <span className="ml-3 font-mono text-xs text-slate-400 hidden sm:inline">
                    focuspilot-engine://session-telemetry
                  </span>
                </div>

                {/* Interactive Mode Tabs */}
                <div className="flex items-center p-1 rounded-xl bg-slate-950/80 border border-white/10 text-xs font-semibold">
                  <button
                    onClick={() => switchTab('deep')}
                    className={`px-3 py-1.5 rounded-lg transition-all ${
                      activeTab === 'deep'
                        ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 shadow-xs'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Deep Work (25m)
                  </button>
                  <button
                    onClick={() => switchTab('sprint')}
                    className={`px-3 py-1.5 rounded-lg transition-all ${
                      activeTab === 'sprint'
                        ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 shadow-xs'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Flow Sprint (50m)
                  </button>
                  <button
                    onClick={() => switchTab('break')}
                    className={`px-3 py-1.5 rounded-lg transition-all ${
                      activeTab === 'break'
                        ? 'bg-teal-500/20 text-teal-300 border border-teal-500/30 shadow-xs'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Recovery Break (5m)
                  </button>
                </div>

                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="font-mono text-xs text-emerald-400 font-semibold uppercase tracking-wider">
                    Extension Synchronized
                  </span>
                </div>
              </div>

              {/* HUD Interior: Split Layout */}
              <div className="p-6 sm:p-8 lg:p-10 grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
                
                {/* Left: 21st.dev Radial Dial Flow Timer */}
                <div className="lg:col-span-5 flex flex-col items-center justify-center p-6 rounded-2xl bg-slate-950/60 border border-white/10 relative overflow-hidden">
                  <div className="absolute inset-0 bg-gradient-to-b from-emerald-500/10 via-transparent to-transparent pointer-events-none" />
                  
                  {/* Circular SVG Dial */}
                  <div className="relative w-56 h-56 flex items-center justify-center">
                    <svg className="w-full h-full -rotate-90 transform" viewBox="0 0 200 200">
                      {/* Track */}
                      <circle
                        cx="100"
                        cy="100"
                        r={radius}
                        className="stroke-slate-800"
                        strokeWidth="10"
                        fill="transparent"
                      />
                      {/* Dynamic Arc */}
                      <circle
                        cx="100"
                        cy="100"
                        r={radius}
                        className={`transition-all duration-700 ease-out ${
                          activeTab === 'break' ? 'stroke-teal-400' : 'stroke-emerald-400'
                        }`}
                        strokeWidth="10"
                        strokeDasharray={circumference}
                        strokeDashoffset={strokeDashoffset}
                        strokeLinecap="round"
                        fill="transparent"
                        style={{
                          filter: 'drop-shadow(0 0 10px rgba(16, 185, 129, 0.45))'
                        }}
                      />
                    </svg>

                    {/* Central Readout */}
                    <div className="absolute inset-0 flex flex-col items-center justify-center text-center select-none">
                      <span className="text-[10px] font-bold tracking-[0.25em] text-emerald-400 uppercase mb-1">
                        {activeTab === 'break' ? 'RECHARGE PHASE' : 'NEURAL FLOW'}
                      </span>
                      <p className="text-5xl font-mono font-bold tracking-tight text-white">
                        {formatTimer(demoSeconds)}
                      </p>
                      <span className="text-xs text-slate-400 mt-1.5 font-medium">
                        {Math.round(progressPercent)}% cycle completed
                      </span>
                    </div>
                  </div>

                  {/* Simulator Controls */}
                  <div className="mt-6 flex items-center gap-3">
                    <button
                      onClick={() => setIsDemoRunning(!isDemoRunning)}
                      className="px-4 py-1.5 rounded-full text-xs font-semibold bg-white/10 hover:bg-white/15 text-white transition flex items-center gap-1.5"
                    >
                      {isDemoRunning ? (
                        <>
                          <svg className="w-3.5 h-3.5 text-amber-400" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                          </svg>
                          Pause Demo
                        </>
                      ) : (
                        <>
                          <svg className="w-3.5 h-3.5 text-emerald-400" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
                          </svg>
                          Resume Demo
                        </>
                      )}
                    </button>
                    <button
                      onClick={() => switchTab(activeTab)}
                      className="px-3 py-1.5 rounded-full text-xs font-medium text-slate-400 hover:text-white transition"
                    >
                      Reset
                    </button>
                  </div>
                </div>

                {/* Right: Live Behavioral Telemetry & Interventions */}
                <div className="lg:col-span-7 space-y-4">
                  {/* ML Risk Gauge */}
                  <div className="p-4 rounded-xl bg-slate-950/80 border border-white/10">
                    <div className="flex items-center justify-between text-xs mb-2">
                      <span className="font-semibold text-slate-300">Live Distraction Vulnerability</span>
                      <span className="font-mono font-bold text-emerald-400">{riskScore}% • Safe Flow Zone</span>
                    </div>
                    <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-emerald-400 to-teal-400 transition-all duration-500 rounded-full"
                        style={{ width: `${riskScore}%` }}
                      />
                    </div>
                  </div>

                  {/* Intercept Event Stream */}
                  <div className="space-y-2.5">
                    <div className="p-3.5 rounded-xl bg-slate-950/70 border border-emerald-500/20 flex items-start gap-3">
                      <div className="mt-0.5 p-1 rounded-md bg-emerald-500/20 text-emerald-400">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                        </svg>
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <p className="text-xs font-bold text-white">Shield Intercept Engaged</p>
                          <span className="text-[10px] font-mono text-slate-500">Just now</span>
                        </div>
                        <p className="text-xs text-slate-400 mt-0.5">
                          Redirected attempt to <span className="text-rose-400 font-mono">x.com</span> → Kept session in Deep Work. Saved ~18 mins.
                        </p>
                      </div>
                    </div>

                    <div className="p-3.5 rounded-xl bg-slate-950/70 border border-white/10 flex items-start gap-3">
                      <div className="mt-0.5 p-1 rounded-md bg-cyan-500/20 text-cyan-400">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                        </svg>
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <p className="text-xs font-bold text-white">Productivity DNA Detection</p>
                          <span className="text-[10px] font-mono text-slate-500">2 min ago</span>
                        </div>
                        <p className="text-xs text-slate-400 mt-0.5">
                          High cognitive velocity: Dwell ratio at 96% on primary code workspace.
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Chronotype Peak Indicator */}
                  <div className="p-3.5 rounded-xl bg-gradient-to-r from-emerald-950/30 to-slate-900 border border-emerald-500/20 flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <span className="text-sm">🦁</span>
                      <div>
                        <p className="text-xs font-bold text-slate-200">Chronotype: Morning Lion</p>
                        <p className="text-[11px] text-slate-400">Peak cognitive window active right now (09:00 - 11:30)</p>
                      </div>
                    </div>
                    <span className="px-2.5 py-1 rounded-full text-[10px] font-semibold bg-emerald-500/20 text-emerald-300">
                      Optimal
                    </span>
                  </div>
                </div>

              </div>

            </div>
          </div>
        </section>

        {/* BENTO GRID: THE 4 PILLARS OF FOCUSPILOT OS */}
        <section id="features" className="mb-28 scroll-mt-28">
          <div className="text-center max-w-2xl mx-auto mb-14">
            <h2 className="text-xs font-bold text-emerald-400 uppercase tracking-[0.2em] mb-3">
              Engineered Architecture
            </h2>
            <p className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
              A productivity system that actually understands human psychology.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
            
            {/* Card 1: 7-col Bento */}
            <div className="md:col-span-7 rounded-3xl p-7 sm:p-8 bg-slate-900/60 border border-white/10 backdrop-blur-xl relative overflow-hidden group hover:border-emerald-500/30 transition-all duration-300">
              <div className="flex items-center justify-between mb-6">
                <span className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                </span>
                <span className="text-xs font-mono text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20">
                  K-Means Behavioral Clusters
                </span>
              </div>
              <h3 className="text-xl sm:text-2xl font-bold text-white mb-2">
                Productivity DNA Fingerprinting
              </h3>
              <p className="text-slate-300 text-sm leading-relaxed mb-6">
                Instead of treating every work session the same, FocusPilot clusters your sessions into distinct behavioral states. It knows when you are in effortless deep work, when tab-switching signals fatigue, and when you require a clean break.
              </p>
              <div className="rounded-xl p-4 bg-slate-950/70 border border-white/10 grid grid-cols-3 gap-2 text-center">
                <div>
                  <p className="text-lg font-bold text-emerald-400">88.4</p>
                  <p className="text-[11px] text-slate-400">Focus Index</p>
                </div>
                <div>
                  <p className="text-lg font-bold text-teal-400">42 min</p>
                  <p className="text-[11px] text-slate-400">Avg Flow Block</p>
                </div>
                <div>
                  <p className="text-lg font-bold text-cyan-400">92%</p>
                  <p className="text-[11px] text-slate-400">Intervention Success</p>
                </div>
              </div>
            </div>

            {/* Card 2: 5-col Bento */}
            <div className="md:col-span-5 rounded-3xl p-7 sm:p-8 bg-slate-900/60 border border-white/10 backdrop-blur-xl relative overflow-hidden group hover:border-emerald-500/30 transition-all duration-300">
              <div className="flex items-center justify-between mb-6">
                <span className="p-2.5 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </span>
                <span className="text-xs font-mono text-cyan-400 bg-cyan-500/10 px-2.5 py-1 rounded-full border border-cyan-500/20">
                  Real-time ML
                </span>
              </div>
              <h3 className="text-xl sm:text-2xl font-bold text-white mb-2">
                4-Factor Distraction Scorer
              </h3>
              <p className="text-slate-300 text-sm leading-relaxed mb-6">
                A multi-layered algorithm continuously computes procrastination risk using tab entropy, dwell cadence, site category, and active cycle context.
              </p>
              <div className="space-y-2 text-xs font-medium">
                <div className="flex justify-between text-slate-300">
                  <span>Tab Switch Frequency</span>
                  <span className="text-emerald-400 font-mono">25%</span>
                </div>
                <div className="flex justify-between text-slate-300">
                  <span>Dwell Duration Ratio</span>
                  <span className="text-emerald-400 font-mono">30%</span>
                </div>
                <div className="flex justify-between text-slate-300">
                  <span>Domain Category Risk</span>
                  <span className="text-emerald-400 font-mono">30%</span>
                </div>
                <div className="flex justify-between text-slate-300">
                  <span>Session Flow Context</span>
                  <span className="text-emerald-400 font-mono">15%</span>
                </div>
              </div>
            </div>

            {/* Card 3: 5-col Bento */}
            <div className="md:col-span-5 rounded-3xl p-7 sm:p-8 bg-slate-900/60 border border-white/10 backdrop-blur-xl relative overflow-hidden group hover:border-emerald-500/30 transition-all duration-300">
              <div className="flex items-center justify-between mb-6">
                <span className="p-2.5 rounded-xl bg-teal-500/10 border border-teal-500/20 text-teal-400">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                </span>
                <span className="text-xs font-mono text-teal-400 bg-teal-500/10 px-2.5 py-1 rounded-full border border-teal-500/20">
                  Manifest V3
                </span>
              </div>
              <h3 className="text-xl sm:text-2xl font-bold text-white mb-2">
                Sub-Millisecond Extension
              </h3>
              <p className="text-slate-300 text-sm leading-relaxed mb-4">
                The lightweight Chrome extension works silently via Chrome Storage and declarative rules. It intercepts distracting triggers without lagging your browser or consuming heavy memory.
              </p>
              <div className="p-3 rounded-xl bg-slate-950/70 border border-white/10 flex items-center gap-3">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
                <span className="text-xs text-slate-300 font-mono">declarativeNetRequest: 0 CPU Overhead</span>
              </div>
            </div>

            {/* Card 4: 7-col Bento */}
            <div className="md:col-span-7 rounded-3xl p-7 sm:p-8 bg-slate-900/60 border border-white/10 backdrop-blur-xl relative overflow-hidden group hover:border-emerald-500/30 transition-all duration-300">
              <div className="flex items-center justify-between mb-6">
                <span className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                </span>
                <span className="text-xs font-mono text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20">
                  RL Policy Engine
                </span>
              </div>
              <h3 className="text-xl sm:text-2xl font-bold text-white mb-2">
                Reinforcement Learning Optimization
              </h3>
              <p className="text-slate-300 text-sm leading-relaxed mb-6">
                FocusPilot uses Q-learning policy feedback loops. Every time an intervention occurs, the system monitors whether your focus recovered. Over time, it learns the exact gentle intervention that works best for your brain.
              </p>
              <div className="p-4 rounded-xl bg-slate-950/70 border border-white/10 flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400 font-mono text-xs font-bold">
                    Q(s,a)
                  </div>
                  <div>
                    <p className="text-xs font-bold text-white">Adaptive Thresholding</p>
                    <p className="text-[11px] text-slate-400">Self-calibrating reward function</p>
                  </div>
                </div>
                <span className="text-xs font-mono text-emerald-400 font-bold bg-emerald-500/10 px-3 py-1 rounded-full">
                  Policy v3.2 Active
                </span>
              </div>
            </div>

          </div>
        </section>

        {/* WHY FOCUSPILOT: COMPARISON MATRIX */}
        <section id="why-focuspilot" className="mb-28 scroll-mt-28">
          <div className="text-center max-w-2xl mx-auto mb-14">
            <h2 className="text-xs font-bold text-emerald-400 uppercase tracking-[0.2em] mb-3">
              The Evolution of Focus
            </h2>
            <p className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
              Why traditional blockers fail — and FocusPilot succeeds.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto">
            {/* The Old Way */}
            <div className="rounded-3xl p-7 bg-slate-900/40 border border-white/5 opacity-80">
              <div className="flex items-center gap-3 mb-5">
                <span className="w-8 h-8 rounded-full bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400 text-sm font-bold">
                  ✕
                </span>
                <h3 className="text-lg font-bold text-slate-300">Traditional Website Blockers</h3>
              </div>
              <ul className="space-y-3.5 text-sm text-slate-400">
                <li className="flex items-start gap-2.5">
                  <span className="text-rose-400 mt-0.5">•</span>
                  <span>Rigid manual blocklists that require constant updating.</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="text-rose-400 mt-0.5">•</span>
                  <span>Zero behavioral intelligence—treats 2-minute research the same as doomscrolling.</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="text-rose-400 mt-0.5">•</span>
                  <span>Easy to disable in moment of weakness; creates frustration and guilt.</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="text-rose-400 mt-0.5">•</span>
                  <span>No circadian awareness or personalized cognitive cycle scheduling.</span>
                </li>
              </ul>
            </div>

            {/* The FocusPilot Way */}
            <div className="rounded-3xl p-7 bg-gradient-to-b from-emerald-500/10 via-slate-900/80 to-slate-900 border border-emerald-500/30 shadow-xl shadow-emerald-500/5">
              <div className="flex items-center gap-3 mb-5">
                <span className="w-8 h-8 rounded-full bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-300 text-sm font-bold">
                  ✓
                </span>
                <h3 className="text-lg font-bold text-white">FocusPilot Autonomous OS</h3>
              </div>
              <ul className="space-y-3.5 text-sm text-slate-200">
                <li className="flex items-start gap-2.5">
                  <span className="text-emerald-400 mt-0.5">•</span>
                  <span>Learns your personal productivity fingerprint and chronotype peaks.</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="text-emerald-400 mt-0.5">•</span>
                  <span>Predicts procrastination spikes <strong>before</strong> they derail your work.</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="text-emerald-400 mt-0.5">•</span>
                  <span>Positive reinforcement with structured cycle plans and recovery breaks.</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="text-emerald-400 mt-0.5">•</span>
                  <span>Reinforcement learning adapts nudges based on what actually recovers your focus.</span>
                </li>
              </ul>
            </div>
          </div>
        </section>

        {/* CTA COMMAND BANNER */}
        <section className="relative rounded-3xl p-8 sm:p-12 lg:p-16 bg-gradient-to-b from-slate-900 to-slate-950 border border-white/10 overflow-hidden text-center shadow-2xl">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-96 h-48 bg-emerald-500/15 rounded-full blur-3xl pointer-events-none" />
          
          <div className="relative z-10 max-w-2xl mx-auto">
            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 mb-6">
              Autonomous Productivity Engine
            </span>
            <h2 className="text-3xl sm:text-5xl font-black text-white tracking-tight leading-tight mb-4">
              Reclaim your focus. <br />
              Own your best work.
            </h2>
            <p className="text-slate-300 text-sm sm:text-base mb-8 max-w-lg mx-auto">
              Join focused professionals using FocusPilot to eliminate cognitive drift and build unbreakable daily momentum.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <button
                onClick={() => navigate('/signup')}
                className="w-full sm:w-auto px-8 py-3.5 rounded-full bg-emerald-400 text-slate-950 font-bold hover:bg-emerald-300 transition shadow-xl shadow-emerald-500/25 active:scale-95 text-base flex items-center justify-center gap-2"
              >
                <span>Launch FocusPilot Free</span>
                <span className="text-xs">↗</span>
              </button>
              <button
                onClick={() => navigate('/login')}
                className="w-full sm:w-auto px-6 py-3.5 rounded-full border border-white/15 hover:bg-white/10 text-slate-200 font-semibold transition text-base"
              >
                Sign In to Existing Account
              </button>
            </div>
          </div>
        </section>

      </main>

      {/* FOOTER */}
      <footer className="border-t border-white/10 bg-slate-950/80 py-10 px-4 sm:px-6 lg:px-8 text-xs text-slate-400">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="font-bold text-white text-sm">FocusPilot</span>
            <span>— AI-Powered Productivity OS</span>
          </div>
          <div className="flex items-center gap-6">
            <a
              href="https://github.com/olatunjitobiloba/FocusPilot"
              target="_blank"
              rel="noreferrer"
              className="hover:text-white transition"
            >
              GitHub Repository
            </a>
            <button onClick={() => navigate('/login')} className="hover:text-white transition">
              Sign In
            </button>
            <button onClick={() => navigate('/signup')} className="hover:text-white transition">
              Sign Up
            </button>
          </div>
          <p>© 2026 FocusPilot. Built for cognitive endurance.</p>
        </div>
      </footer>
    </div>
  );
}
