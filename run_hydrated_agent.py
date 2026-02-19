import os
import ray
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

@ray.remote
class HydratedAgent:
    def __init__(self, agent_id: str, system_message: str):
        self.agent_id = agent_id
        
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is missing!")

        self.model_client = OpenAIChatCompletionClient(
            model="gpt-4o-mini", 
            api_key=api_key
        )
        
        self.agent = AssistantAgent(
            name=self.agent_id,
            model_client=self.model_client,
            system_message=system_message
        )

    async def process_message(self, user_input: str) -> str:
        print(f"[{self.agent_id}] Processing message: '{user_input}'")
        result = await self.agent.run(task=user_input)
        return result.messages[-1].content

if __name__ == "__main__":
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Please export OPENAI_API_KEY='your-key' in your terminal first.")
        exit(1)

    print("Connecting to Project Pneuma Ray Cluster...")
    
    cluster_env = {
        "env_vars": {"OPENAI_API_KEY": api_key},
        "pip": [
            "autogen-agentchat>=0.4.0",
            "autogen-ext[openai]>=0.4.0"
        ]
    }
    
    # Initialize connection with the new runtime_env
    ray.init("ray://localhost:10001", runtime_env=cluster_env)
    print("Connected successfully! (Cluster is provisioning dependencies...)\n")

    print("Deploying HydratedAgent to a worker node...")
    agent_actor = HydratedAgent.remote(
        agent_id="Agent_Pioneer", # <--- Changed to an underscore
        system_message="You are the first AI agent awakened in Project Pneuma. Keep your response to one short sentence."
    )

    print("Sending transmission to Agent-Pioneer...")
    
    # We use ray.get() to wait for the remote async function to resolve
    response = ray.get(agent_actor.process_message.remote("Hello, are you online?"))
    
    print("\n--- Agent Response ---")
    print(response)

    ray.shutdown()