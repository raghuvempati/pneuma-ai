import uuid
from typing import List, Dict
from sentence_transformers import SentenceTransformer
from qdrant_client.models import PointStruct
from src.database import DatabaseManager
from src.config import VECTOR_COLLECTION

class PneumaRegistry:
    def __init__(self):
        self.db = DatabaseManager()
        # Ensure schema exists on init
        self.db.init_schema()
        # Local embedding model (Apache 2.0)
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')

    def register_agent(self, name: str, role: str, skills: str) -> str:
        agent_id = str(uuid.uuid4())
        
        # 1. Embed Semantic Profile
        text_repr = f"{role}. Expert in: {skills}"
        vector = self.embedder.encode(text_repr).tolist()

        # 2. Write to Graph (Storage)
        # Escape strings for nGQL
        safe_values = [x.replace('"', '\\"') for x in [name, role, skills]]
        query = f'INSERT VERTEX agent(name, role, skills, state_snapshot) VALUES "{agent_id}": ("{safe_values[0]}", "{safe_values[1]}", "{safe_values[2]}", "{{}}")'
        self.db.execute_graph(query)

        # 3. Write to Vector DB (Index)
        self.db.vector_client.upsert(
            collection_name=VECTOR_COLLECTION,
            points=[PointStruct(
                id=agent_id,
                vector=vector,
                payload={"name": name, "role": role, "skills": skills}
            )]
        )
        return agent_id

    def find_agents(self, query: str, limit: int = 1) -> List[Dict]:
        """Semantic Search for Agents"""
        query_vec = self.embedder.encode(query).tolist()
        hits = self.db.vector_client.search(
            collection_name=VECTOR_COLLECTION,
            query_vector=query_vec,
            limit=limit
        )
        return [{"id": h.id, "name": h.payload["name"], "role": h.payload["role"], "score": h.score} for h in hits]

    def create_link(self, from_id: str, to_id: str, reason: str):
        safe_reason = reason.replace('"', '\\"')
        query = f'INSERT EDGE KNOWS(reason, weight) VALUES "{from_id}"->"{to_id}": ("{safe_reason}", 1.0)'
        self.db.execute_graph(query)