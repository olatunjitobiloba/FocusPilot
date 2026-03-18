from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.ml.agent.orchestrator import orchestrator
from app.ml.agent.scheduler import action_scheduler
from app.routes import auth, sessions, agent as agent_router, stats, blocklist, analytics as analytics_router, recommendations, suggestions, health, whitelist, ml_data, settings, predictions, decisions, executions as execution_router, pipeline as pipeline_router, dna as dna_router, rl as rl_router
from app.database import get_supabase

app = FastAPI(
    title="FocusPilot Agent API",
    version="0.1.0",
    description="Autonomous AI agent for focus tracking"
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://focuspilot.vercel.app",
        "https://*.vercel.app",           # All Vercel preview deployments
        "http://localhost:3000",           # Local development
        "http://localhost:5173",           # Vite dev server
        "chrome-extension://*",           # Chrome extension
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(agent_router.router)
app.include_router(stats.router)
app.include_router(blocklist.router)
app.include_router(analytics_router.router)
app.include_router(recommendations.router)
app.include_router(suggestions.router)
app.include_router(health.router)
app.include_router(whitelist.router)
app.include_router(ml_data.router)
app.include_router(settings.router)
app.include_router(predictions.router)
app.include_router(decisions.router)
app.include_router(execution_router.router)
app.include_router(pipeline_router.router)
app.include_router(dna_router.router)
app.include_router(rl_router.router)


@app.on_event("startup")
async def startup_event():
    orchestrator.start()
    action_scheduler.start()
    print("✅ Agent Orchestrator + Scheduler started")


@app.on_event("shutdown")
async def shutdown_event():
    orchestrator.stop()
    action_scheduler.stop()
    print("Monitoring Agent Orchestrator + Scheduler stopped")

@app.get("/")
def root():
    return {
        "message": "FocusPilot Autonomous Agent API",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/test-db")
def test_db():
    try:
        supabase = get_supabase()
        result = supabase.table('users').select("count", count='exact').execute()
        return {
            "status": "connected",
            "user_count": result.count
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
