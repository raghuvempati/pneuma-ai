import sys
import ray
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT / "src"))

from pneuma.core.config import settings
from pneuma.memory.vector_store import SemanticMemory
from pneuma.topology.graph_store import SharedBrain
from pneuma.orchestration.dispatcher import TaskDispatcher

if __name__ == "__main__":
    print("Connecting to Project Pneuma Infrastructure via Central Config...")
    
    # 1. Connect to Ray using the centralized API key
    cluster_env = {
        "working_dir": str(PROJECT_ROOT / "src"),
        "env_vars": {
            "OPENAI_API_KEY": settings.openai_api_key,
            "OPENAI_MODEL": settings.openai_model,
        },
        "pip": ["autogen-agentchat>=0.4.0", "autogen-ext[openai]>=0.4.0", "nebula3-python>=3.8.0"]
    }
    ray.init("ray://localhost:10001", runtime_env=cluster_env)
    
    # 2. Connect to Memory using centralized routing
    memory = SemanticMemory(host=settings.qdrant_host, port=settings.qdrant_port)
    brain = SharedBrain(host=settings.nebula_host, port=settings.nebula_port)
    
    dispatcher = TaskDispatcher(memory=memory, brain=brain)

    task = "Write a Python script to check if a string is a palindrome."
    print(f"\n--- Incoming Task ---\n{task}\n")

    final_answer = dispatcher.execute_single_task(task)

    print("\n--- Final System State ---")
    print(final_answer)

    brain.close()
    ray.shutdown()
