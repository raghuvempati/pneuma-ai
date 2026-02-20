import sys
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT / "src"))

from pneuma.core.config import settings
from pneuma.topology.graph_store import SharedBrain

if __name__ == "__main__":
    print("Connecting to Project Pneuma Shared Brain for Schema Migration...")
    
    brain = SharedBrain(host=settings.nebula_host, port=settings.nebula_port)
    session = brain.get_session()
    
    try:
        brain._run(session, 'USE pneuma_brain;')
        
        print("Executing ALTER TAG command to add 'result' property...")
        # This forcefully injects the new property into the existing tag
        brain._run(session, 'ALTER TAG Task ADD (result string);')
        
        print("Migration successful! The Task tag now supports the 'result' column.")
    except Exception as e:
        print(f"Migration failed (or was already applied): {e}")
    finally:
        session.release()
        brain.close()
