from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import ray

from pneuma.core.config import settings
from pneuma.memory.vector_store import SemanticMemory
from pneuma.topology.graph_store import SharedBrain
from pneuma.orchestration.dispatcher import TaskDispatcher

from pneuma.middleware.guardrails import SecurityGuardrail

# --- Data Models ---
class TaskRequest(BaseModel):
    task: str = Field(..., description="The objective or prompt for the AI agent(s)")
    timeout: int = Field(120, description="Circuit breaker timeout in seconds")

class SwarmRequest(TaskRequest):
    threshold: float = Field(0.30, description="Minimum confidence score to draft an agent into the swarm")

class TaskResponse(BaseModel):
    status: str
    result: str

# --- Application Lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup and shutdown events for the API."""
    print("\n[API] Booting Project Pneuma Orchestrator...")

    # 0. Initialize Security Guardrails
    app.state.guardrail = SecurityGuardrail()  
    
    # 1. Connect to Infrastructure
    app.state.memory = SemanticMemory(host=settings.qdrant_host, port=settings.qdrant_port)
    app.state.brain = SharedBrain(host=settings.nebula_host, port=settings.nebula_port)
    app.state.dispatcher = TaskDispatcher(memory=app.state.memory, brain=app.state.brain)

    # 2. Connect to the KubeRay Cluster (via your local port-forward for now)
    cluster_env = {
        "working_dir": "/".join(__file__.split("/")[:-3]), # Points to src/
        "env_vars": {
            "OPENAI_API_KEY": settings.openai_api_key,
            "OPENAI_MODEL": settings.openai_model
        },
        "pip": ["autogen-agentchat>=0.4.0", "autogen-ext[openai]>=0.4.0", "nebula3-python>=3.8.0"]
    }
    
    print(f"[API] Connecting to KubeRay cluster at {settings.ray_address}...")
    ray.init(settings.ray_address, runtime_env=cluster_env)
    
    print("[API] Pneuma Orchestrator is LIVE and ready for requests.\n")
    yield # The API runs while yielded
    
    # --- Teardown ---
    print("\n[API] Shutting down Pneuma Orchestrator...")
    app.state.brain.close()
    ray.shutdown()

# --- API Initialization ---
app = FastAPI(
    title="Project Pneuma API",
    description="REST interface for massive-scale agent swarm orchestration.",
    version="1.0.0",
    lifespan=lifespan
)

# --- Routes ---
@app.get("/health")
async def health_check():
    """Liveness probe for Kubernetes."""
    return {"status": "healthy", "ray_connected": ray.is_initialized()}

@app.post("/api/v1/task", response_model=TaskResponse)
async def execute_single_task(request: TaskRequest):
    try:
        # NEW: Force the prompt through the guardrail before anything else happens
        safe_task = app.state.guardrail.process_input(request.task)
        
        result = app.state.dispatcher.execute_single_task(
            task=safe_task, 
            timeout=request.timeout
        )
        return TaskResponse(status="success", result=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/swarm", response_model=TaskResponse)
async def execute_swarm(request: SwarmRequest):
    try:
        # NEW: Force the prompt through the guardrail
        safe_task = app.state.guardrail.process_input(request.task)
        
        result = app.state.dispatcher.execute_swarm_pipeline(
            task=safe_task, 
            threshold=request.threshold, 
            timeout=request.timeout
        )
        return TaskResponse(status="success", result=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))