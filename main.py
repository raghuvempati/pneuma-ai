import asyncio
import ray
from src.registry import PneumaRegistry
from src.orchestrator import SwarmOrchestrator

def genesis():
    """Populates the empty universe with dormant agents."""
    reg = PneumaRegistry()
    
    # Check if empty (naive check) using vector client
    try:
        info = reg.db.vector_client.get_collection("agent_vectors")
        if info.points_count > 0:
            print("🌍 Pneuma World already populated.")
            return
    except:
        pass

    print("✨ GENESIS: Creating Dormant Agents...")
    agents = [
        ("Alice", "Frontend Architect", "React, TypeScript, Tailwind, UX Design"),
        ("Bob", "Backend Engineer", "Python, FastAPI, Postgres, Redis"),
        ("Charlie", "DevOps Specialist", "Docker, Kubernetes, AWS, Terraform"),
        ("Diana", "Product Owner", "Agile, User Stories, Market Research"),
        ("Eve", "Security Analyst", "PenTesting, OAuth, OWASP Top 10")
    ]
    
    for n, r, s in agents:
        reg.register_agent(n, r, s)
    print("✅ Genesis Complete.")

async def main():
    # 1. Init Ray
    ray.init(ignore_reinit_error=True)
    
    # 2. Setup World
    genesis()
    
    # 3. Run Mission
    orchestrator = SwarmOrchestrator.remote()
    
    mission = "Design a secure, scalable login system for a banking app."
    roles = ["Frontend Architect", "Backend Engineer", "Security Analyst"]
    
    print("\n⚡ PNEUMA: Waking Agents...")
    result = await orchestrator.run_mission.remote(mission, roles)
    
    print("\n📜 MISSION LOG:")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())