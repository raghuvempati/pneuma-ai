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
        print("[Dispatcher] Consulting Shared Brain for previous solutions...")
        cached_result = self.brain.recall_memory(task)
        if cached_result:
            return f"[CACHED RECALL] {cached_result}"

        discovered = self.memory.discover_agents(task, limit=1)
        if not discovered:
            return "Error: No suitable agents found in semantic memory."
        
        best_match = discovered[0]
        agent_id = best_match["agent_id"]
        system_message = best_match["description"]
        
        print(f"[Dispatcher] Selected {agent_id} (Confidence Score: {best_match['score']:.4f})")
        print(f"[Dispatcher] Hydrating {agent_id} on Ray cluster...")

        agent_actor = HydratedAgent.remote(agent_id=agent_id, system_message=system_message)

        try:
            print(f"[Dispatcher] Routing task to {agent_id} (with {timeout}s Circuit Breaker)...")
            
            # THE FIX: Add a hard 120-second timeout to the Ray execution
            response = ray.get(agent_actor.process_message.remote(task), timeout=timeout)
            
            print(f"[Dispatcher] Committing execution memory to Shared Brain...")
            self.brain.insert_execution_record(
                agent_id=agent_id, 
                agent_role=system_message, 
                task_desc=task,
                task_result=response
            )
            
        except GetTimeoutError:
            response = f"Error: Circuit Breaker tripped. {agent_id} exceeded the 120-second timeout."
            print(f"[Dispatcher] {response}")
        except Exception as e:
            response = f"Error during execution: {str(e)}"
            print(f"[Dispatcher] {response}")
        
        # This cleanup step now acts as our fail-safe to free cluster RAM 
        # even if the agent timed out or crashed.
        print(f"[Dispatcher] Task complete or terminated. Spinning down {agent_id}.")
        ray.kill(agent_actor)
        
        return response
    
    def execute_swarm_pipeline(self, task: str, threshold: float = 0.35, limit: int = 3) -> str:
        """Discovers multiple qualified agents, hydrates a swarm, and pipelines the task."""
        
        # 1. Ask Qdrant for the top 3 potential candidates
        discovered = self.memory.discover_agents(task, limit=limit)
        
        # 2. Filter the draft picks based on the confidence threshold
        swarm_draft = [agent for agent in discovered if agent["score"] >= threshold]
        
        if not swarm_draft:
            return "Error: No agents met the confidence threshold for this task."

        print(f"\n[Dispatcher] Assembling Swarm of {len(swarm_draft)} agents...")
        active_actors = []

        # 3. Hydrate the entire swarm on the Ray cluster
        for match in swarm_draft:
            agent_id = match["agent_id"]
            print(f"[Dispatcher] -> Hydrating {agent_id} (Score: {match['score']:.4f})")
            actor = HydratedAgent.remote(
                agent_id=agent_id,
                system_message=match["description"]
            )
            active_actors.append((agent_id, actor))

        # 4. Execute the Pipeline (Map-Reduce style collaboration)
        current_context = task
        
        for step, (agent_id, actor) in enumerate(active_actors):
            print(f"\n[Dispatcher] Routing to {agent_id} (Step {step + 1}/{len(active_actors)})...")
            
            # If it's the first agent, they get the raw task. 
            # Subsequent agents get the task PLUS the previous agent's output.
            if step == 0:
                prompt = f"Task: {task}"
            else:
                prompt = f"Original Task: {task}\n\nPrevious Agent Output to review/build upon:\n{current_context}\n\nPlease improve, verify, or add your specific expertise to this."
            
            try:
                # Wait for this specific node to finish its compute
                current_context = ray.get(actor.process_message.remote(prompt))
            except Exception as e:
                current_context = f"Error during {agent_id} execution: {str(e)}"
                break # Break the pipeline on failure

        # 5. Swarm Teardown
        print("\n[Dispatcher] Swarm objective complete. Spinning down all actors.")
        for _, actor in active_actors:
            ray.kill(actor)

        return current_context