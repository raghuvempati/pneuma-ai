import os
import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from openai import OpenAI
from pneuma.core.config import settings


class SemanticMemory:
    def __init__(self, host=settings.qdrant_host, port=settings.qdrant_port):
        self.client = QdrantClient(host=host, port=port)
        self.openai_client = OpenAI(api_key=settings.openai_api_key)
        
        self.agent_collection = "pneuma_agents"
        self.cache_collection = "task_cache" # NEW: Collection for past tasks
        
        self._ensure_collection(self.agent_collection)
        self._ensure_collection(self.cache_collection)

    def _ensure_collection(self, collection_name: str):
        if not self.client.collection_exists(collection_name):
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
            )

    # def _initialize_collection(self):
    #     """Ensures the collection exists with the correct vector dimensions."""
    #     if not self.client.collection_exists(collection_name=self.collection_name):
    #         # OpenAI's text-embedding-3-small produces 1536-dimensional vectors
    #         self.client.create_collection(
    #             collection_name=self.collection_name,
    #             vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
    #         )
    #         print(f"Collection '{self.collection_name}' created successfully.")
    #     else:
    #         print(f"Collection '{self.collection_name}' already exists and is ready.")

    def get_embedding(self, text: str) -> list[float]:
        response = self.openai_client.embeddings.create(
            input=text, model="text-embedding-3-small"
        )
        return response.data[0].embedding

    def register_agent(self, agent_id: str, description: str):
        import uuid
        vector = self.get_embedding(description)
        
        # Generate a deterministic UUID based on the string name
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, agent_id))
        
        self.client.upsert(
            collection_name=self.agent_collection,
            points=[
                PointStruct(
                    id=point_id, 
                    vector=vector, 
                    payload={"agent_id": agent_id, "description": description} # Tuck the real ID in the payload
                )
            ]
        )

    def discover_agents(self, task_description: str, limit: int = 1) -> list[dict]:
        # Updated parameter to task_description to match the dispatcher
        query_vector = self.get_embedding(task_description)
        hits = self.client.search(
            collection_name=self.agent_collection,
            query_vector=query_vector,
            limit=limit
        )
        
        return [
            {
                "agent_id": hit.payload["agent_id"], 
                "description": hit.payload["description"], 
                "score": hit.score
            } 
            for hit in hits
        ]
    
    def cache_task_intent(self, task_desc: str, task_id: str):
        """Saves the mathematical intent of a task to Qdrant, linked to its Graph ID."""
        import uuid
        vector = self.get_embedding(task_desc)
        
        self.client.upsert(
            collection_name=self.cache_collection,
            points=[
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload={"task_id": task_id, "original_desc": task_desc}
                )
            ]
        )

    def search_cached_intent(self, task_desc: str, similarity_threshold: float = 0.95) -> str | None:
        """Searches for a past task with nearly identical intent."""
        query_vector = self.get_embedding(task_desc)
        
        hits = self.client.search(
            collection_name=self.cache_collection,
            query_vector=query_vector,
            limit=1,
            score_threshold=similarity_threshold
        )
        
        if hits:
            print(f"[Semantic Cache] Intent matched with score {hits[0].score:.4f}!")
            return hits[0].payload["task_id"]
        return None
