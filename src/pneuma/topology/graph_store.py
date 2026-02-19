import time
from nebula3.gclient.net import ConnectionPool
from nebula3.Config import Config

class SharedBrain:
    def __init__(self, host="127.0.0.1", port=9669):
        self.config = Config()
        self.config.max_connection_pool_size = 10
        self.pool = ConnectionPool()
        
        if not self.pool.init([(host, port)], self.config):
            raise ConnectionError(f"Failed to connect to NebulaGraph at {host}:{port}")
            
    def get_session(self):
        return self.pool.get_session('root', 'nebula')

    def _run(self, session, query):
        """Hardened query execution that strictly raises exceptions on database failure."""
        result = session.execute(query)
        if not result.is_succeeded():
            raise Exception(f"NebulaGraph Error: {result.error_msg()} \nFailed Query: {query}")
        return result

    def initialize_schema(self):
        print("[SharedBrain] Initializing NebulaGraph Schema...")
        session = self.get_session()
        try:
            self._run(session, 'CREATE SPACE IF NOT EXISTS pneuma_brain(partition_num=1, replica_factor=1, vid_type=FIXED_STRING(64));')
            print("[SharedBrain] Space 'pneuma_brain' created/verified.")
            
            # Increased sleep: Docker clusters often need 10+ seconds to sync new spaces
            print("[SharedBrain] Waiting 10 seconds for cluster schema synchronization...")
            time.sleep(10) 
            
            self._run(session, 'USE pneuma_brain;')
            self._run(session, 'CREATE TAG IF NOT EXISTS Agent(role string);')
            self._run(session, 'CREATE TAG IF NOT EXISTS Task(description string, status string);')
            self._run(session, 'CREATE EDGE IF NOT EXISTS EXECUTED(executed_at int);')
            self._run(session, 'CREATE EDGE IF NOT EXISTS COLLABORATED_WITH(project string);')
            print("[SharedBrain] Schema initialization complete.")
        finally:
            session.release()

    def insert_execution_record(self, agent_id: str, agent_role: str, task_desc: str):
        import uuid
        import time
        
        task_id = f"task_{uuid.uuid4().hex[:16]}"
        timestamp = int(time.time())
        
        session = self.get_session()
        try:
            self._run(session, 'USE pneuma_brain;')
            
            safe_role = agent_role.replace('"', "'")
            safe_desc = task_desc.replace('"', "'")
            
            self._run(session, f'INSERT VERTEX Agent(role) VALUES "{agent_id}":("{safe_role}");')
            self._run(session, f'INSERT VERTEX Task(description, status) VALUES "{task_id}":("{safe_desc}", "Completed");')
            self._run(session, f'INSERT EDGE EXECUTED(executed_at) VALUES "{agent_id}"->"{task_id}":({timestamp});')
            
            print(f"[SharedBrain] Successfully mapped {agent_id} -> EXECUTED -> {task_id}")
        finally:
            session.release()

    def close(self):
        self.pool.close()