import os
import ray
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT / "src"))
from pneuma.core.agent import HydratedAgent

if __name__ == "__main__":
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Please export OPENAI_API_KEY='your-key' in your terminal first.")
        exit(1)

    cluster_env = {
        "env_vars": {"OPENAI_API_KEY": api_key},
        "pip": ["autogen-agentchat>=0.4.0", "autogen-ext[openai]>=0.4.0"]
    }
    
    print("Connecting to Project Pneuma Ray Cluster...")
    ray.init("ray://localhost:10001", runtime_env=cluster_env)

    agent_actor = HydratedAgent.remote(
        agent_id="Agent_Pioneer",
        system_message="You are the first AI agent awakened in Project Pneuma. Keep your response to one short sentence."
    )

    response = ray.get(agent_actor.process_message.remote("Hello, are you online?"))
    print(f"\nResponse: {response}")
    ray.shutdown()