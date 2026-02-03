from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api.routes import chat, trials, agents
from app.services.clinical_trials_api import clinical_trials_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"Starting {settings.PROJECT_NAME}...")
    yield
    # Shutdown
    await clinical_trials_service.close()
    print("Shutdown complete.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI-powered clinical trial matching system with multi-agent architecture",
    version="0.1.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:3000",
        "http://localhost:5678",  # n8n
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    chat.router,
    prefix=f"{settings.API_V1_STR}/chat",
    tags=["Chat"]
)

app.include_router(
    trials.router,
    prefix=f"{settings.API_V1_STR}/trials",
    tags=["Trials"]
)

app.include_router(
    agents.router,
    prefix=f"{settings.API_V1_STR}/agents",
    tags=["Agents (n8n)"]
)


@app.get("/")
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
