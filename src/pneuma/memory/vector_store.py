import os
import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from openai import OpenAI


class SemanticMemory:
    def __init__(self, host="localhost", port=6333, collection_name="agent_profiles"):
        # Connect to the Qdrant instance running on Docker Desktop
        self.client = QdrantClient(host=host, port=port)
        self.collection_name = collection_name
        self.openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

        self._initialize_collection()

    def _initialize_collection(self):
        """Ensures the collection exists with the correct vector dimensions."""
        if not self.client.collection_exists(collection_name=self.collection_name):
            # OpenAI's text-embedding-3-small produces 1536-dimensional vectors
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
            )
            print(f"Collection '{self.collection_name}' created successfully.")
        else:
            print(f"Collection '{self.collection_name}' already exists and is ready.")

    def get_embedding(self, text: str) -> list[float]:
        """Converts text into a vector using OpenAI."""
        response = self.openai_client.embeddings.create(
            input=text, model="text-embedding-3-small"
        )
        return response.data[0].embedding

    def register_agent(self, agent_id: str, capabilities_description: str):
        """Embeds an agent's capabilities and stores it in Qdrant."""
        vector = self.get_embedding(capabilities_description)

        # Qdrant requires a UUID or integer ID. We hash the agent_id to create a stable UUID.
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, agent_id))

        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "agent_id": agent_id,
                        "description": capabilities_description,
                    },
                )
            ],
        )
        print(f"Agent '{agent_id}' registered in semantic memory.")

    def discover_agents(self, task_description: str, limit: int = 2) -> list[dict]:
        """Finds the most relevant agents for a given task based on vector similarity."""
        query_vector = self.get_embedding(task_description)

        hits = self.client.search(
            collection_name=self.collection_name, query_vector=query_vector, limit=limit
        )

        # ADDED: Extract the description from the payload so we can use it as the system prompt
        return [
            {
                "agent_id": hit.payload["agent_id"],
                "description": hit.payload["description"],
                "score": hit.score,
            }
            for hit in hits
        ]
