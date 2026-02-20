import sys
import ray
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT / "src"))

from pneuma.core.config import settings
from pneuma.memory.vector_store import SemanticMemory
from pneuma.topology.graph_store import SharedBrain
from pneuma.orchestration.dispatcher import TaskDispatcher

if __name__ == "__main__":
    try:
        api_key = settings.openai_api_key
    except ValueError as e:
        print(e)
        exit(1)

    print("Connecting to Project Pneuma Infrastructure...")
    
    # 1. Connect to Compute (Ray)
    cluster_env = {
        "working_dir": str(PROJECT_ROOT / "src"),
        "env_vars": {
            "OPENAI_API_KEY": api_key,
            "OPENAI_MODEL": settings.openai_model,
        },
        "pip": ["autogen-agentchat>=0.4.0", "autogen-ext[openai]>=0.4.0", "nebula3-python>=3.8.0"]
    }
    ray.init("ray://localhost:10001", runtime_env=cluster_env)
    
    # 2. Connect to Semantic Memory (Qdrant)
    memory = SemanticMemory(host=settings.qdrant_host, port=settings.qdrant_port)
    
    # 3. Connect to Topological Memory (NebulaGraph)
    brain = SharedBrain(host=settings.nebula_host, port=settings.nebula_port)
    
    # 4. Initialize Orchestrator
    dispatcher = TaskDispatcher(memory=memory, brain=brain)

    task = "Write a Python script that prints the first 100 prime numbers."
    print(f"\n--- Incoming Task ---\n{task}\n")

    # Let the framework orchestrate Phase 1 through 4 automatically
    final_answer = dispatcher.execute_single_task(task)

    print("\n--- Final Agent Response ---")
    print(final_answer)

    # Clean up connections
    brain.close()
    ray.shutdown()
