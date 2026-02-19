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