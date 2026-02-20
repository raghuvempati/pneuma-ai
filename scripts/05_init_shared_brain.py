import sys
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT / "src"))

from pneuma.core.config import settings
from pneuma.topology.graph_store import SharedBrain

if __name__ == "__main__":
    print("Connecting to Project Pneuma NebulaGraph Instance...")
    
    try:
        brain = SharedBrain(host=settings.nebula_host, port=settings.nebula_port)
        brain.initialize_schema()
        brain.close()
        print("\nSuccess: The Shared Brain is online and ready for data.")
    except Exception as e:
        print(f"\nError: {e}")
        print("Did you remember to run: kubectl port-forward svc/pneuma-graph-graphd 9669:9669 ?")
