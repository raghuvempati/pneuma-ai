import time
from nebula3.gclient.net import ConnectionPool
from nebula3.Config import Config

class SharedBrain:
    def __init__(self, host="127.0.0.1", port=9669):
        self.config = Config()
        self.config.max_connection_pool_size = 10
        self.pool = ConnectionPool()
        
        # Connect to the local port-forwarded Nebula Graphd service
        if not self.pool.init([(host, port)], self.config):
            raise ConnectionError("Failed to connect to NebulaGraph at {}:{}".format(host, port))
            
    def get_session(self):
        # Correct NebulaGraph client method
        return self.pool.get_session('root', 'nebula')

    def initialize_schema(self):
        """Creates the foundational graph topology for Project Pneuma."""
        print("[SharedBrain] Initializing NebulaGraph Schema...")
        
        session = self.get_session()
        try:
            # 1. Create the Space (Database)
            session.execute('CREATE SPACE IF NOT EXISTS pneuma_brain(partition_num=1, replica_factor=1, vid_type=FIXED_STRING(64));')
            print("[SharedBrain] Space 'pneuma_brain' created/verified.")
            
            # Nebula requires a brief sleep after creating a space before using it
            time.sleep(5) 
            session.execute('USE pneuma_brain;')
            
            # 2. Define Tags (Nodes)
            session.execute('CREATE TAG IF NOT EXISTS Agent(role string);')
            session.execute('CREATE TAG IF NOT EXISTS Task(description string, status string);')
            print("[SharedBrain] Node schemas (Agent, Task) created.")
            
            # 3. Define Edges (Relationships)
            session.execute('CREATE EDGE IF NOT EXISTS EXECUTED(timestamp int);')
            session.execute('CREATE EDGE IF NOT EXISTS COLLABORATED_WITH(project string);')
            print("[SharedBrain] Edge schemas (EXECUTED, COLLABORATED_WITH) created.")
            
            print("[SharedBrain] Schema initialization complete.")
            
        finally:
            # Crucial: Explicitly release the session back to the pool
            session.release()

    def close(self):
        self.pool.close()