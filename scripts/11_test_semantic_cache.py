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
    print("Connecting to Project Pneuma Infrastructure...")
    
    cluster_env = {
        "working_dir": str(PROJECT_ROOT / "src"),
        "env_vars": {
            "OPENAI_API_KEY": settings.openai_api_key,
            "OPENAI_MODEL": settings.openai_model
        },
        "pip": ["autogen-agentchat>=0.4.0", "autogen-ext[openai]>=0.4.0", "nebula3-python>=3.8.0"]
    }
    ray.init("ray://localhost:10001", runtime_env=cluster_env)
    
    memory = SemanticMemory(host=settings.qdrant_host, port=settings.qdrant_port)
    brain = SharedBrain(host=settings.nebula_host, port=settings.nebula_port)
    dispatcher = TaskDispatcher(memory=memory, brain=brain)

    # --- TASK 1: THE INITIAL RUN ---
    task_1 = "Write a Python function to compute the first 50 numbers of the Fibonacci sequence."
    print(f"\n=========================================")
    print(f"TASK 1 (Initial Compute): {task_1}")
    print(f"=========================================")
    result_1 = dispatcher.execute_single_task(task_1)
    
    # --- TASK 2: THE SEMANTIC VARIATION ---
    task_2 = "Can you give me a python script that prints out 50 fibonacci numbers?"
    print(f"\n=========================================")
    print(f"TASK 2 (Semantic Variation): {task_2}")
    print(f"=========================================")
    result_2 = dispatcher.execute_single_task(task_2)

    print("\n--- Final Test Output ---")
    # If the system works, result_2 should be identical to result_1 and prefixed with [SEMANTIC CACHE RECALL]
    print(result_2)

    brain.close()
    ray.shutdown()