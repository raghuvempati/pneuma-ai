import ray
import time
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core import CancellationToken

# IMPORT THE CENTRALIZED SETTINGS
from pneuma.core.config import settings 

@ray.remote
class HydratedAgent:
    def __init__(self, agent_id: str, system_message: str):
        self.agent_id = agent_id
        self.system_message = system_message
        
        self.model_client = OpenAIChatCompletionClient(
            model=settings.openai_model,
            api_key=settings.openai_api_key
        )
        
        self.agent = AssistantAgent(
            name=self.agent_id,
            model_client=self.model_client,
            system_message=self.system_message
        )

    async def process_message(self, task: str) -> str:
        """Executes the task with a built-in retry mechanism for API resilience."""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Execute the AutoGen task
                response = await self.agent.on_messages(
                    [TextMessage(content=task, source="user")],
                    cancellation_token=CancellationToken()
                )
                return response.chat_message.content
                
            except Exception as e:
                print(f"[{self.agent_id}] API Error on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt == max_retries - 1:
                    raise Exception(f"Task failed after {max_retries} attempts. Last error: {e}")
                
                # Exponential backoff: sleep 2 seconds, then 4 seconds...
                time.sleep(2 ** (attempt + 1))