import sys
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT / "src"))

from pneuma.core.config import settings
from pneuma.topology.graph_store import SharedBrain

if __name__ == "__main__":
    print("Connecting to Project Pneuma NebulaGraph Instance...")
    brain = SharedBrain(host=settings.nebula_host, port=settings.nebula_port)
    session = brain.get_session()
    
    try:
        session.execute('USE pneuma_brain;')
        
        query = """
        MATCH (a:Agent)-[e:EXECUTED]->(t:Task) 
        RETURN id(a) AS AgentID, a.Agent.role AS role, t.Task.description AS Task 
        LIMIT 10;
        """
        
        print("\n[SharedBrain] Executing Memory Retrieval Query...")
        result = brain._run(session, query)
        
        if not result.is_empty():
            print("\n--- Retrieved Topological Memories ---")
            for memory in result.as_primitive():
                print(f"Agent : {memory['AgentID']}")
                print(f"Role  : {memory['role']}") # <-- Lowercase 'r'
                print(f"Task  : {memory['Task']}")
                print("-" * 50)
        else:
            print("No memories found. The graph is empty.")
            
    finally:
        session.release()
        brain.close()
