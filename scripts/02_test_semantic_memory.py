import sys
from pathlib import Path

# Add src to the Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT / "src"))

from pneuma.core.config import settings
from pneuma.memory.vector_store import SemanticMemory

if __name__ == "__main__":
    try:
        settings.openai_api_key
    except ValueError as e:
        print(e)
        exit(1)

    print("Connecting to Qdrant Semantic Memory...")
    # Initialize our Qdrant wrapper
    memory = SemanticMemory(host=settings.qdrant_host, port=settings.qdrant_port)

    # 1. Register agents into the vector database
    print("\nRegistering agent profiles...")
    memory.register_agent("Agent_PythonExpert", "Expert in writing, debugging, and optimizing Python code, including asynchronous programming and decorators.")
    memory.register_agent("Agent_DevOpsEngineer", "Specialist in Kubernetes, Docker, CI/CD pipelines, and infrastructure as code.")
    memory.register_agent("Agent_DataAnalyst", "Skilled in Pandas, NumPy, SQL, data visualization, and statistical modeling.")

    # 2. Simulate a dynamic discovery event
    task = "I need help writing a script to deploy my application to a Kubernetes cluster using a Helm chart."
    print(f"\nIncoming Task: '{task}'")
    print("Searching vector space for the most qualified agent...")

    # Query Qdrant
    discovered_agents = memory.discover_agents(task_description=task, limit=1)

    print("\n--- Discovery Results ---")
    for match in discovered_agents:
        print(f"Selected Agent: {match['agent_id']} (Confidence Score: {match['score']:.4f})")
