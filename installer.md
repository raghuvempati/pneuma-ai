# Project Pneuma: Local Infrastructure Setup Guide

**Execution Environment:** MacBook Pro M3 (Apple Silicon / ARM64)
**Platform:** Docker Desktop with Kubernetes enabled

## Pre-requisites: Docker Desktop Tuning

Running a graph database, a vector database, and a distributed compute engine simultaneously requires adequate resources. 
1. Open Docker Desktop -> **Settings** -> **Resources** -> **Advanced**.
2. Ensure Docker has at least **6 CPUs** and **8 GB of Memory** allocated to avoid silent Out-Of-Memory (OOM) kills.
3. Apply and restart Docker.

---

## 1. NebulaGraph (The Topology)

We use the official Nebula Operator to manage the complex startup sequence of the graph, meta, and storage nodes.

### Install the Operator

```bash
helm repo add nebula-operator [https://vesoft-inc.github.io/nebula-operator/charts](https://vesoft-inc.github.io/nebula-operator/charts)
helm repo update
helm install nebula-operator nebula-operator/nebula-operator --namespace=nebula-operator-system --create-namespace
```

### Apply the Cluster Manifest (k8s/pneuma-graph.yaml)

***Note: Uses v3.8.0 for native ARM64 support.***

```yaml
apiVersion: apps.nebula-graph.io/v1alpha1
kind: NebulaCluster
metadata:
  name: pneuma-graph
  namespace: default
spec:
  graphd:
    replicas: 1
    image: vesoft/nebula-graphd
    version: v3.8.0
    resources:
      requests:
        cpu: "200m"
        memory: "500Mi"
    service:
      type: LoadBalancer
      externalTrafficPolicy: Local
  metad:
    replicas: 1
    image: vesoft/nebula-metad
    version: v3.8.0
    dataVolumeClaim:
      resources:
        requests:
          storage: 1Gi
    resources:
      requests:
        cpu: "200m"
        memory: "500Mi"
  storaged:
    replicas: 1
    image: vesoft/nebula-storaged
    version: v3.8.0
    dataVolumeClaims:
      - resources:
          requests:
            storage: 2Gi
    resources:
      requests:
        cpu: "200m"
        memory: "500Mi"
```

```bash
kubectl apply -f pneuma-nebula.yaml
```

---

## 2. Qdrant (Semantic Discovery)

Deployed as a lightweight StatefulSet with a persistent volume to ensure agent vector embeddings survive pod restarts.

### Apply the Manifest (pneuma-qdrant.yaml)

***Note: Natively pulls the ARM64 image for Apple Silicon.***

```yaml
apiVersion: v1
kind: Service
metadata:
  name: qdrant-service
  namespace: default
spec:
  type: LoadBalancer
  ports:
    - name: http
      port: 6333
      targetPort: 6333
    - name: grpc
      port: 6334
      targetPort: 6334
  selector:
    app: qdrant
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: pneuma-qdrant
  namespace: default
spec:
  serviceName: "qdrant-service"
  replicas: 1
  selector:
    matchLabels:
      app: qdrant
  template:
    metadata:
      labels:
        app: qdrant
    spec:
      containers:
      - name: qdrant
        image: qdrant/qdrant:v1.12.0
        ports:
        - containerPort: 6333
        - containerPort: 6334
        resources:
          requests:
            cpu: "200m"
            memory: "500Mi"
        volumeMounts:
        - mountPath: /qdrant/storage
          name: qdrant-storage
  volumeClaimTemplates:
  - metadata:
      name: qdrant-storage
    spec:
      accessModes: [ "ReadWriteOnce" ]
      resources:
        requests:
          storage: 2Gi
```

```bash
kubectl apply -f pneuma-qdrant.yaml
```

***Verify via browser at http://localhost:6333/dashboard.***

---

## 3. Ray (Dynamic Orchestration)

The execution engine for agent swarms. Uses KubeRay and explicitly targets Python 3.12 and Ray 2.54.0.

### Install the KubeRay Operator

```bash
helm repo add kuberay [https://ray-project.github.io/kuberay-helm/](https://ray-project.github.io/kuberay-helm/)
helm repo update
helm install kuberay-operator kuberay/kuberay-operator --version 1.1.0
```

### Apply the Ray Cluster Manifest (pneuma-ray.yaml)

***Critical Fixes Included: Shared memory (/dev/shm) mounts to prevent Object Store crashes, explicitly exposed Head Node ports to allow worker/client connections, and ARM64-specific Python 3.12 tags.***

```yaml
apiVersion: ray.io/v1
kind: RayCluster
metadata:
  name: pneuma-ray
  namespace: default
spec:
  rayVersion: '2.54.0'
  headGroupSpec:
    rayStartParams:
      dashboard-host: '0.0.0.0'
    template:
      spec:
        volumes:
          - name: dshm
            emptyDir:
              medium: Memory
        containers:
          - name: ray-head
            image: rayproject/ray:2.54.0-py312-aarch64
            resources:
              requests:
                cpu: "500m"
                memory: "2Gi" # Increased memory
            ports:
              - containerPort: 8265
                name: dashboard
              - containerPort: 10001
                name: client
              - containerPort: 6379
                name: gcs
            volumeMounts:
              - mountPath: /dev/shm
                name: dshm
  workerGroupSpecs:
    - replicas: 1
      minReplicas: 1
      maxReplicas: 3
      groupName: standard-workers
      rayStartParams: {}
      template:
        spec:
          volumes:
            - name: dshm
              emptyDir:
                medium: Memory
          containers:
            - name: ray-worker
              image: rayproject/ray:2.54.0-py312-aarch64
              resources:
                requests:
                  cpu: "500m"
                  memory: "1Gi"
              volumeMounts:
                - mountPath: /dev/shm
                  name: dshm
```

```bash
kubectl apply -f pneuma-ray.yaml
```

***Verify via browser at http://localhost:8265.***

---

## 4. Verification & Client Connection

To run tasks from the local macOS environment into the Kubernetes Ray cluster, the local Python environment must perfectly match the cluster.

### Local Environment Setup

```bash
# Ensure you are using Python 3.12
pip install "ray[default]==2.54.0"
```

### Open the Connection Bridge

You must port-forward the Ray Client port from the Kubernetes service to your local machine before executing scripts:

```bash
kubectl port-forward svc/pneuma-ray-head-svc 10001:10001
```

### Verification Script (test_pneuma.py)

Run this to confirm distributed execution across the Head and Worker pods.

```python
import ray
import socket
import time
from collections import Counter

print("Connecting to Project Pneuma Ray Cluster (Python 3.12)...")
# Connects via the active port-forward tunnel
ray.init("ray://localhost:10001") 
print("Connected successfully!\n")

@ray.remote(num_cpus=0.1)
def get_execution_node_ip():
    time.sleep(0.5) 
    return socket.gethostbyname(socket.gethostname())

print("Dispatching 10 concurrent tasks to the cluster...")
futures = [get_execution_node_ip.remote() for _ in range(10)]

results = ray.get(futures)
execution_counts = Counter(results)

print("\n--- Distributed Execution Report ---")
for ip, count in execution_counts.items():
    print(f"Node IP {ip} executed {count} tasks")

ray.shutdown()
```

