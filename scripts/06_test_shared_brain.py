import os
import sys
import ray
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT / "src"))

from pneuma.memory.vector_store import SemanticMemory
from pneuma.topology.graph_store import SharedBrain
from pneuma.orchestration.dispatcher import TaskDispatcher

if __name__ == "__main__":
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Please export OPENAI_API_KEY='your-key' in your terminal first.")
        exit(1)

    print("Connecting to Project Pneuma Infrastructure...")
    
    # 1. Connect to Compute (Ray)
    cluster_env = {
        "working_dir": str(PROJECT_ROOT / "src"),
        "env_vars": {"OPENAI_API_KEY": api_key},
        "pip": ["autogen-agentchat>=0.4.0", "autogen-ext[openai]>=0.4.0", "nebula3-python>=3.8.0"]
    }
    ray.init("ray://localhost:10001", runtime_env=cluster_env)
    
    # 2. Connect to Semantic Memory (Qdrant)
    memory = SemanticMemory(host="localhost", port=6333)
    
    # 3. Connect to Topological Memory (NebulaGraph)
    brain = SharedBrain(host="127.0.0.1", port=9669)
    
    # 4. Initialize Orchestrator
    dispatcher = TaskDispatcher(memory=memory, brain=brain)

    task = "Write a Python script that calculates the Fibonacci sequence up to 100."
    print(f"\n--- Incoming Task ---\n{task}\n")

    # Let the framework orchestrate Phase 1 through 4 automatically
    final_answer = dispatcher.execute_single_task(task)

    print("\n--- Final Agent Response ---")
    print(final_answer)

    # Clean up connections
    brain.close()
    ray.shutdown()