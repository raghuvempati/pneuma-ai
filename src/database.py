import time
import json
from nebula3.gclient.net import ConnectionPool
from nebula3.Config import Config
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from src.config import *

class DatabaseManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._init_connections()
        return cls._instance

    def _init_connections(self):
        # 1. Nebula Graph
        config = Config()
        config.max_connection_pool_size = 10
        self.graph_pool = ConnectionPool()
        assert self.graph_pool.init(NEBULA_HOSTS, config)
        
        # 2. Qdrant
        self.vector_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

    def init_schema(self):
        """Idempotent Schema Creation"""
        # Nebula Schema
        with self.graph_pool.session_context(NEBULA_USER, NEBULA_PASSWORD) as session:
            session.execute(f"CREATE SPACE IF NOT EXISTS {GRAPH_SPACE} (partition_num=10, replica_factor=1, vid_type=FIXED_STRING(64));")
            time.sleep(3) # Wait for heartbeat
            session.execute(f"USE {GRAPH_SPACE};")
            session.execute("CREATE TAG IF NOT EXISTS agent (name string, role string, skills string, state_snapshot string);")
            session.execute("CREATE EDGE IF NOT EXISTS KNOWS (reason string, weight double);")
        
        # Qdrant Schema
        if not self.vector_client.collection_exists(VECTOR_COLLECTION):
            self.vector_client.create_collection(
                collection_name=VECTOR_COLLECTION,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )

    def execute_graph(self, query):
        with self.graph_pool.session_context(NEBULA_USER, NEBULA_PASSWORD) as session:
            session.execute(f"USE {GRAPH_SPACE}")
            return session.execute(query)