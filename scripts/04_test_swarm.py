import os
import sys
import ray
from pathlib import Path

# Setup paths and environment
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT / "src"))

from pneuma.memory.vector_store import SemanticMemory
from pneuma.orchestration.dispatcher import TaskDispatcher

if __name__ == "__main__":
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Please export OPENAI_API_KEY='your-key' in your terminal first.")
        exit(1)

    print("Connecting to Project Pneuma Infrastructure...")
    
    cluster_env = {
        "working_dir": str(PROJECT_ROOT / "src"),
        "env_vars": {"OPENAI_API_KEY": api_key},
        "pip": ["autogen-agentchat>=0.4.0", "autogen-ext[openai]>=0.4.0"]
    }
    ray.init("ray://localhost:10001", runtime_env=cluster_env)
    
    memory = SemanticMemory(host="localhost", port=6333)
    dispatcher = TaskDispatcher(memory=memory)

    # A complex task designed to cross semantic boundaries
    task = "I need a Python script using FastAPI that serves a simple 'Hello World' endpoint. I also need the Dockerfile and Kubernetes deployment YAML to deploy this specific API."
    print(f"\n--- Incoming Complex Task ---\n{task}\n")

    # Fire the swarm pipeline!
    final_answer = dispatcher.execute_swarm_pipeline(task, threshold=0.35)

    print("\n--- Final Swarm Intelligence Response ---")
    print(final_answer)

    ray.shutdown()