import ray
import socket
import time
from collections import Counter

# 1. Connect to the Ray cluster via our port-forwarded tunnel
print("Connecting to Project Pneuma Ray Cluster...")
ray.init("ray://localhost:10001")
print("Connected successfully!\n")

# 2. Define the atomic task
# We request a tiny fraction of a CPU to ensure Ray can run many at once
@ray.remote(num_cpus=0.1)
def get_execution_node_ip():
    # A tiny sleep forces Ray to distribute the tasks rather than 
    # letting one node process them sequentially in a millisecond
    time.sleep(0.5) 
    return socket.gethostbyname(socket.gethostname())

# 3. Fire off the swarm
print("Dispatching 10 concurrent tasks to the cluster...")
futures = [get_execution_node_ip.remote() for _ in range(10)]

# 4. Wait for the results to return to the Mac
results = ray.get(futures)

# 5. Tally up where the work actually happened
execution_counts = Counter(results)

print("\n--- Distributed Execution Report ---")
for ip, count in execution_counts.items():
    print(f"Node IP {ip} executed {count} tasks")

# Disconnect cleanly
ray.shutdown()