import sys
import ray
from pathlib import Path

# Add src to the Python path
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
    
    # Init Ray with the working_dir so it syncs our src folder
    cluster_env = {
        "working_dir": str(PROJECT_ROOT / "src"),
        "env_vars": {
            "OPENAI_API_KEY": api_key,
            "OPENAI_MODEL": settings.openai_model,
        },
        "pip": ["autogen-agentchat>=0.4.0", "autogen-ext[openai]>=0.4.0"]
    }
    ray.init("ray://localhost:10001", runtime_env=cluster_env)
    
    # Init Memory
    memory = SemanticMemory(host=settings.qdrant_host, port=settings.qdrant_port)
    brain = SharedBrain(host=settings.nebula_host, port=settings.nebula_port)
    
    # Init the new Orchestrator
    dispatcher = TaskDispatcher(memory=memory, brain=brain)

    # We registered our agents in script 02, so they are already in Qdrant!
    task = "Write a Python function that uses a decorator to retry a failed API call 3 times before giving up."
    print(f"\n--- Incoming Task ---\n{task}\n")

    # Let the framework handle the rest
    final_answer = dispatcher.execute_single_task(task)

    print("\n--- Final Agent Response ---")
    print(final_answer)

    brain.close()
    ray.shutdown()
