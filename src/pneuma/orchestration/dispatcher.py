import ray
from pneuma.core.agent import HydratedAgent
from pneuma.memory.vector_store import SemanticMemory
from pneuma.topology.graph_store import SharedBrain
from ray.exceptions import GetTimeoutError

class TaskDispatcher:
    # 1. Require the SharedBrain upon initialization
    def __init__(self, memory: SemanticMemory, brain: SharedBrain):
        self.memory = memory
        self.brain = brain

    def execute_single_task(self, task: str, timeout: int = 120) -> str:
        # 1. NEW: SEMANTIC INTENT CHECK (Qdrant)
        print("\n[Dispatcher] Checking Semantic Cache for similar past intents...")
        cached_task_id = self.memory.search_cached_intent(task, similarity_threshold=0.92)
        
        # 2. NEW: GRAPH RETRIEVAL (NebulaGraph)
        if cached_task_id:
            print(f"[Dispatcher] Intent match found! Fetching result from Graph ID: {cached_task_id}")
            cached_result = self.brain.recall_memory_by_id(cached_task_id)
            if cached_result:
                return f"[SEMANTIC CACHE RECALL]\n{cached_result}"
            else:
                print("[Dispatcher] Graph node missing despite vector match. Proceeding to compute...")

        # 3. Standard Semantic Discovery
        discovered = self.memory.discover_agents(task, limit=1)
        if not discovered:
            return "Error: No suitable agents found in semantic memory."
        
        best_match = discovered[0]
        agent_id = best_match["agent_id"]
        system_message = best_match["description"]
        
        print(f"[Dispatcher] Selected {agent_id} (Confidence Score: {best_match['score']:.4f})")
        print(f"[Dispatcher] Hydrating {agent_id} on Ray cluster...")

        actor = HydratedAgent.remote(agent_id=agent_id, system_message=system_message)

        try:
            print(f"[Dispatcher] Routing task to {agent_id} (with {timeout}s Circuit Breaker)...")
            response = ray.get(actor.process_message.remote(task), timeout=timeout)
            
            # 4. NEW: DUAL-WRITE COMMIT
            print("[Dispatcher] Task complete. Committing execution to Shared Brain (Graph)...")
            task_id = self.brain.insert_execution_record(
                agent_id=agent_id, 
                agent_role=system_message, 
                task_desc=task,
                task_result=response
            )
            
            print(f"[Dispatcher] Linking intent to Task ID '{task_id}' in Vector Cache...")
            self.memory.cache_task_intent(task_desc=task, task_id=task_id)
            
        except ray.exceptions.GetTimeoutError:
            response = f"Error: Circuit Breaker tripped. {agent_id} exceeded the {timeout}-second timeout."
            print(f"[Dispatcher] {response}")
        except Exception as e:
            response = f"Error during execution: {str(e)}"
            print(f"[Dispatcher] {response}")
        
        print(f"[Dispatcher] Spinning down {agent_id}.")
        ray.kill(actor)
        
        return response
    
    def execute_swarm_pipeline(self, task: str, threshold: float = 0.35, timeout: int = 120) -> str:
        """Discovers multiple agents, hydrates a swarm, pipelines the task, and caches the result."""
        
        # 1. MEMORY-FIRST ROUTING
        print("[Dispatcher] Consulting Shared Brain for previous swarm solutions...")
        cached_result = self.brain.recall_memory(task)
        if cached_result:
            return f"[CACHED RECALL] {cached_result}"
        
        # 2. SEMANTIC SWARM DISCOVERY
        discovered = self.memory.discover_agents(task, limit=3)
        swarm_draft = [agent for agent in discovered if agent["score"] >= threshold]
        
        if not swarm_draft:
            return "Error: No agents met the confidence threshold for this task."

        print(f"\n[Dispatcher] Assembling Swarm of {len(swarm_draft)} agents...")
        active_actors = []

        # 3. PARALLEL HYDRATION
        for match in swarm_draft:
            agent_id = match["agent_id"]
            print(f"[Dispatcher] -> Hydrating {agent_id} (Score: {match['score']:.4f})")
            actor = HydratedAgent.remote(agent_id=agent_id, system_message=match["description"])
            # Keep track of id, role, and the physical Ray actor
            active_actors.append((agent_id, match["description"], actor))

        # 4. PIPELINE EXECUTION WITH CIRCUIT BREAKERS
        current_context = task
        swarm_agent_ids = []
        
        for step, (agent_id, role, actor) in enumerate(active_actors):
            swarm_agent_ids.append(agent_id)
            print(f"\n[Dispatcher] Routing to {agent_id} (Step {step + 1}/{len(active_actors)})...")
            
            if step == 0:
                prompt = f"Task: {task}"
            else:
                prompt = f"Original Task: {task}\n\nPrevious Agent Output to review/build upon:\n{current_context}\n\nPlease improve, verify, or add your specific expertise to this."
            
            try:
                # The Circuit Breaker protects each individual step of the swarm
                current_context = ray.get(actor.process_message.remote(prompt), timeout=timeout)
            except Exception as e:
                current_context = f"Error during {agent_id} execution: {str(e)}"
                print(f"[Dispatcher] {current_context}")
                break # If one agent fails or times out, break the pipeline

        # 5. COMMIT COLLABORATIVE MEMORY
        print("\n[Dispatcher] Swarm objective complete. Committing to Shared Brain...")
        
        # We create a composite ID so the database knows it was a joint effort
        composite_swarm_id = f"Swarm({'+'.join(swarm_agent_ids)})"
        
        self.brain.insert_execution_record(
            agent_id=composite_swarm_id, 
            agent_role="Dynamic Pipeline Swarm", 
            task_desc=task,
            task_result=current_context
        )

        # 6. SWARM TEARDOWN
        print("[Dispatcher] Spinning down all swarm actors to free cluster RAM.")
        for _, _, actor in active_actors:
            ray.kill(actor)

        return current_context