import ray
import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.conditions import TextMentionTermination
from src.registry import PneumaRegistry
from src.config import MODEL_NAME

@ray.remote
class SwarmOrchestrator:
    def __init__(self):
        self.registry = PneumaRegistry()
        self.model_client = OpenAIChatCompletionClient(model=MODEL_NAME)

    async def run_mission(self, mission_goal: str, required_roles: list):
        print(f"🚀 PNEUMA: Initializing Mission -> '{mission_goal}'")
        
        team_agents = []
        agent_ids = {} # name -> uuid

        # 1. Recruit
        for role_query in required_roles:
            candidates = self.registry.find_agents(role_query, limit=1)
            if candidates:
                data = candidates[0]
                print(f"   + Hydrating: {data['name']} ({data['role']})")
                
                # In a real app, load 'state_snapshot' from Nebula here
                agent = AssistantAgent(
                    name=data["name"],
                    model_client=self.model_client,
                    system_message=f"You are a {data['role']}. Mission: {mission_goal}"
                )
                team_agents.append(agent)
                agent_ids[data["name"]] = data["id"]

        if not team_agents:
            return "Mission Aborted: No agents found."

        # 2. Execute Swarm
        termination = TextMentionTermination("TERMINATE")
        team = RoundRobinGroupChat(
            participants=team_agents,
            termination_condition=termination,
            max_turns=10
        )

        logs = []
        async for msg in team.run_stream(task=mission_goal):
            if hasattr(msg, 'content') and msg.content:
                logs.append(f"{msg.source}: {msg.content}")

        # 3. Disperse & Link (Knowledge Graph Building)
        # Everyone who worked together now 'KNOWS' each other
        names = list(agent_ids.keys())
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                id_a = agent_ids[names[i]]
                id_b = agent_ids[names[j]]
                self.registry.create_link(id_a, id_b, reason=f"Collaborated on: {mission_goal[:30]}")

        return "\n".join(logs)