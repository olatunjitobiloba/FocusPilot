import React from 'react';
import { useNavigate } from 'react-router-dom';

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen relative overflow-hidden bg-slate-950 text-slate-100">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -top-44 -left-40 h-96 w-96 rounded-full bg-emerald-400/30 blur-3xl" />
        <div className="absolute top-1/3 -right-28 h-80 w-80 rounded-full bg-emerald-400/20 blur-3xl" />
        <div className="absolute bottom-0 left-1/4 h-72 w-72 rounded-full bg-green-500/20 blur-3xl" />
      </div>

      <nav className="relative border-b border-white/10 bg-slate-950/75 backdrop-blur-md">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <button
              onClick={() => navigate('/')}
              className="text-2xl font-black tracking-tight text-white"
              style={{ fontFamily: "'Space Grotesk', 'Sora', sans-serif" }}
            >
              FocusPilot
            </button>
            <div className="flex gap-3">
              <button
                onClick={() => navigate('/login')}
                className="px-4 py-2 rounded-lg border border-white/20 text-white/90 hover:bg-white/10 transition"
              >
                Log In
              </button>
              <button
                onClick={() => navigate('/signup')}
                className="px-5 py-2 rounded-lg bg-emerald-300 text-slate-900 font-semibold hover:bg-emerald-200 transition"
              >
                Start Free
              </button>
            </div>
          </div>
        </div>
      </nav>

      <main className="relative max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10 lg:py-20">
        <section className="grid lg:grid-cols-2 gap-8 lg:gap-10 items-center">
          <div>
            <p className="inline-flex items-center rounded-full border border-emerald-300/40 bg-emerald-300/10 px-3 py-1 text-xs uppercase tracking-[0.2em] text-emerald-200 mb-4 sm:mb-5">
              Adaptive Productivity AI
            </p>
            <h1
              className="text-4xl sm:text-5xl lg:text-6xl font-black leading-[1.03] text-white"
              style={{ fontFamily: "'Space Grotesk', 'Sora', sans-serif" }}
            >
              Stop drifting.
              <br />
              Work in sharp focus blocks.
            </h1>
            <p className="mt-4 sm:mt-5 text-base sm:text-lg text-slate-300 max-w-xl">
              FocusPilot watches your behavior patterns and intervenes before distraction derails your session.
            </p>
            <div className="mt-6 sm:mt-8 flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
              <button
                onClick={() => navigate('/signup')}
                className="w-full sm:w-auto px-7 py-3 rounded-lg bg-emerald-300 text-slate-900 font-bold hover:bg-emerald-200 transition shadow-[0_10px_30px_rgba(110,231,183,0.35)]"
              >
                Launch Dashboard
              </button>
              <button
                onClick={() => navigate('/login')}
                className="w-full sm:w-auto px-7 py-3 rounded-lg border border-white/20 text-white hover:bg-white/10 transition"
              >
                Existing Account
              </button>
            </div>
            <div className="mt-6 sm:mt-8 grid grid-cols-1 sm:grid-cols-3 gap-3 max-w-xl">
              <Metric value="30m" label="Early warning" />
              <Metric value="4x" label="Interventions" />
              <Metric value="24/7" label="Session coverage" />
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-slate-900/80 p-5 sm:p-6 lg:p-7 backdrop-blur-sm shadow-2xl">
            <p className="text-xs tracking-[0.15em] uppercase text-emerald-200/90 mb-4">Live Session Snapshot</p>
            <div className="space-y-4">
              <StatusRow
                title="Context Detection"
                subtitle="Focus confidence raised to 82%"
                tone="emerald"
              />
              <StatusRow
                title="Risk Predictor"
                subtitle="Procrastination risk spike in 26 min"
                tone="amber"
              />
              <StatusRow
                title="Agent Action"
                subtitle="Prompt + site block recommendation queued"
                tone="green"
              />
            </div>
            <div className="mt-5 h-2 rounded-full bg-white/10 overflow-hidden">
              <div className="h-full w-4/5 bg-gradient-to-r from-emerald-300 to-green-300" />
            </div>
            <p className="mt-2 text-xs text-slate-400">Updated every 8 seconds while your focus session is active.</p>
          </div>
        </section>

        <section className="mt-14 grid md:grid-cols-3 gap-4">
          <FeatureCard
            title="Behavior-aware sessions"
            body="Interventions adapt to your rhythm, so nudges arrive when they can still change the outcome."
            accent="bg-emerald-300"
          />
          <FeatureCard
            title="Reinforcement learning engine"
            body="Every action gets scored, turning your daily habits into a policy that improves over time."
            accent="bg-emerald-300"
          />
          <FeatureCard
            title="Decision timeline"
            body="See exactly when the agent intervened, what it did, and whether your focus recovered."
            accent="bg-green-300"
          />
        </section>

        <section className="mt-10 sm:mt-14 rounded-2xl border border-white/10 bg-gradient-to-r from-slate-900 to-slate-800 p-5 sm:p-6 lg:p-8 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 sm:gap-6">
          <div>
            <h2
              className="text-2xl sm:text-3xl font-black text-white"
              style={{ fontFamily: "'Space Grotesk', 'Sora', sans-serif" }}
            >
              Build momentum with fewer resets
            </h2>
            <p className="mt-2 text-slate-300 max-w-2xl">
              Join sessions in under a minute and let FocusPilot handle proactive recovery before attention drops.
            </p>
          </div>
          <button
            onClick={() => navigate('/signup')}
            className="w-full sm:w-auto px-6 py-3 rounded-lg bg-emerald-300 text-slate-900 font-bold hover:bg-emerald-200 transition whitespace-nowrap"
          >
            Create Account
          </button>
        </section>
      </main>
    </div>
  );
}

function Metric({ value, label }: { value: string; label: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/5 p-3">
      <p className="text-xl font-extrabold text-emerald-200">{value}</p>
      <p className="text-xs text-slate-300">{label}</p>
    </div>
  );
}

function StatusRow({
  title,
  subtitle,
  tone
}: {
  title: string;
  subtitle: string;
  tone: 'emerald' | 'amber' | 'green';
}) {
  const toneClasses: Record<'emerald' | 'amber' | 'green', string> = {
    emerald: 'bg-emerald-300',
    amber: 'bg-amber-300',
    green: 'bg-green-300'
  };

  return (
    <div className="rounded-xl border border-white/10 bg-white/5 p-3 flex items-start gap-3">
      <div className={`mt-1 h-2.5 w-2.5 rounded-full ${toneClasses[tone]}`} />
      <div>
        <p className="text-sm font-semibold text-white">{title}</p>
        <p className="text-xs text-slate-300">{subtitle}</p>
      </div>
    </div>
  );
}

function FeatureCard({
  title,
  body,
  accent
}: {
  title: string;
  body: string;
  accent: string;
}) {
  return (
    <div className="relative rounded-xl border border-white/10 bg-slate-900/70 p-5 overflow-hidden">
      <div className={`absolute -top-6 -right-6 h-16 w-16 rounded-full opacity-30 ${accent}`} />
      <h3 className="text-lg font-bold text-white mb-2">{title}</h3>
      <p className="text-sm text-slate-300">{body}</p>
    </div>
  );
}
