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
            
            print("[SharedBrain] Waiting 10 seconds for cluster schema synchronization...")
            time.sleep(10) 
            
            self._run(session, 'USE pneuma_brain;')
            self._run(session, 'CREATE TAG IF NOT EXISTS Agent(role string);')
            self._run(session, 'CREATE TAG IF NOT EXISTS Task(description string, status string, result string);')
            
            self._run(session, 'CREATE TAG INDEX IF NOT EXISTS task_desc_idx ON Task(description(256));')
            
            print("[SharedBrain] Polling cluster until index metadata synchronizes...")
            max_attempts = 30
            for attempt in range(max_attempts):
                # We use the raw session.execute here so we can catch the failure without crashing
                result = session.execute('REBUILD TAG INDEX task_desc_idx;')
                
                if result.is_succeeded():
                    print(f"[SharedBrain] Index synced and rebuilt successfully on attempt {attempt + 1}.")
                    break
                
                # If we exhaust all attempts, THEN we crash and surface the error
                if attempt == max_attempts - 1:
                    raise Exception(f"Index sync timed out. Last error: {result.error_msg()}")
                
                # Wait 1 second before asking again
                time.sleep(1)

            self._run(session, 'CREATE EDGE IF NOT EXISTS EXECUTED(executed_at int);')
            self._run(session, 'CREATE EDGE IF NOT EXISTS COLLABORATED_WITH(project string);')
            
            print("[SharedBrain] Schema initialization complete. Indexes are active.")
        finally:
            session.release()

    def insert_execution_record(self, agent_id: str, agent_role: str, task_desc: str, task_result: str) -> str:
        import uuid
        import time
        
        task_id = f"task_{uuid.uuid4().hex[:16]}"
        timestamp = int(time.time())
        
        session = self.get_session()
        try:
            self._run(session, 'USE pneuma_brain;')
            safe_role = agent_role.replace('"', "'").replace("\n", " ")
            safe_desc = task_desc.replace('"', "'").replace("\n", " ")
            safe_result = task_result.replace('"', "'").replace("\n", " ")
            
            self._run(session, f'INSERT VERTEX Agent(role) VALUES "{agent_id}":("{safe_role}");')
            self._run(session, f'INSERT VERTEX Task(description, status, result) VALUES "{task_id}":("{safe_desc}", "Completed", "{safe_result}");')
            self._run(session, f'INSERT EDGE EXECUTED(executed_at) VALUES "{agent_id}"->"{task_id}":({timestamp});')
            
            print(f"[SharedBrain] Successfully mapped {agent_id} -> EXECUTED -> {task_id}")
            
            return task_id
        finally:
            session.release()

    def recall_memory(self, task_desc: str) -> str | None:
        """Queries the graph to see if this exact task has already been solved."""
        session = self.get_session()
        try:
            self._run(session, 'USE pneuma_brain;')
            safe_desc = task_desc.replace('"', "'").replace("\n", " ")
            
            # Look for a Task node with a matching description
            query = f'MATCH (t:Task) WHERE t.Task.description == "{safe_desc}" RETURN t.Task.result AS result LIMIT 1;'
            result = self._run(session, query)
            
            if not result.is_empty():
                memories = result.as_primitive()
                if memories:
                    print(f"[SharedBrain] Memory Recall Successful! Found cached result for task.")
                    return memories[0].get('result')
            return None
        finally:
            session.release()

    def recall_memory_by_id(self, task_id: str) -> str | None:
        """O(1) retrieval of a task result using its exact physical Graph ID."""
        session = self.get_session()
        try:
            self._run(session, 'USE pneuma_brain;')
            
            query = f'MATCH (t:Task) WHERE id(t) == "{task_id}" RETURN t.Task.result AS result;'
            result = self._run(session, query)
            
            if not result.is_empty() and result.as_primitive():
                return result.as_primitive()[0].get('result')
            return None
        finally:
            session.release()

    def close(self):
        self.pool.close()