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
    
    cluster_env = {
        "working_dir": str(PROJECT_ROOT / "src"),
        "env_vars": {
            "OPENAI_API_KEY": api_key,
            "OPENAI_MODEL": settings.openai_model,
        },
        "pip": ["autogen-agentchat>=0.4.0", "autogen-ext[openai]>=0.4.0", "nebula3-python>=3.8.0"]
    }
    ray.init("ray://localhost:10001", runtime_env=cluster_env)
    
    memory = SemanticMemory(host=settings.qdrant_host, port=settings.qdrant_port)
    brain = SharedBrain(host=settings.nebula_host, port=settings.nebula_port)
    dispatcher = TaskDispatcher(memory=memory, brain=brain)

    # A brand new task so it bypasses our Shared Brain cache
    task = "Write a comprehensive 5-page essay on the history of quantum computing algorithms."
    print(f"\n--- Incoming Task ---\n{task}\n")

    # Injecting chaos: The agent has exactly 2 seconds to write 5 pages.
    final_answer = dispatcher.execute_single_task(task, timeout=2)

    print("\n--- Final System State ---")
    print(final_answer)

    brain.close()
    ray.shutdown()
