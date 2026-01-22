import os
from dotenv import load_dotenv

load_dotenv()

# Infrastructure
NEBULA_HOSTS = [('127.0.0.1', 9669)]
NEBULA_USER = "root"
NEBULA_PASSWORD = "nebula"
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333

# Logic
GRAPH_SPACE = "pneuma_world"
VECTOR_COLLECTION = "agent_vectors"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = "gpt-4o-mini"