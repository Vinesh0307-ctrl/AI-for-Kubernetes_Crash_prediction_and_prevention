import time
import requests
from kubernetes import client, config

# -----------------------------
# CONFIGURATION
# -----------------------------
PREDICT_URL = "http://localhost:8080/predict"  # FastAPI service endpoint
NAMESPACE = "default"  # namespace of the pods you want to monitor
SLEEP_INTERVAL = 10     # seconds between metric checks
FAILURE_THRESHOLD = 0.5 # probability threshold to take action

# -----------------------------
# KUBERNETES CLIENT SETUP
# -----------------------------
# Load cluster config (works inside pod if using ServiceAccount)
try:
    config.load_incluster_config()  # when running inside k8s
except:
    config.load_kube_config()       # local dev

v1 = client.CoreV1Api()
metrics_client = client.CustomObjectsApi()  # for metrics.k8s.io API

# -----------------------------
# HELPER FUNCTIONS
# -----------------------------
def fetch_pod_metrics(pod_name, namespace=NAMESPACE):
    """Fetch CPU and memory usage metrics for a pod from metrics-server"""
    try:
        metrics = metrics_client.get_namespaced_custom_object(
            group="metrics.k8s.io",
            version="v1beta1",
            namespace=namespace,
            plural="pods",
            name=pod_name
        )
        container_metrics = metrics["containers"][0]  # first container
        cpu_usage = container_metrics["usage"]["cpu"]
        mem_usage = container_metrics["usage"]["memory"]
        
        # Convert CPU from n cores or m (millicores) to float cores
        if cpu_usage.endswith("n"):
            cpu = int(cpu_usage[:-1]) / 1e9
        elif cpu_usage.endswith("m"):
            cpu = int(cpu_usage[:-1]) / 1000
        else:
            cpu = float(cpu_usage)
        
        # Convert memory to bytes
        if mem_usage.endswith("Ki"):
            memory = int(mem_usage[:-2]) * 1024
        elif mem_usage.endswith("Mi"):
            memory = int(mem_usage[:-2]) * 1024 * 1024
        elif mem_usage.endswith("Gi"):
            memory = int(mem_usage[:-2]) * 1024 * 1024 * 1024
        else:
            memory = int(mem_usage)
        
        return cpu, memory
    except Exception as e:
        print(f"[ERROR] Could not fetch metrics for {pod_name}: {e}")
        return None, None

def predict_failure(features):
    """Call the ML API to predict pod failure"""
    try:
        response = requests.post(PREDICT_URL, json=features, timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"[ERROR] Prediction API returned {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"[ERROR] Prediction request failed: {e}")
        return None

def restart_pod(pod_name, namespace=NAMESPACE):
    """Delete the pod to trigger Kubernetes to recreate it"""
    try:
        v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
        print(f"[INFO] Pod {pod_name} deleted for restart.")
    except Exception as e:
        print(f"[ERROR] Failed to restart pod {pod_name}: {e}")

# -----------------------------
# MAIN MONITOR LOOP
# -----------------------------
def monitor_pods():
    while True:
        pods = v1.list_namespaced_pod(namespace=NAMESPACE, label_selector="")
        for pod in pods.items:
            pod_name = pod.metadata.name
            cpu, memory = fetch_pod_metrics(pod_name)
            if cpu is None:
                continue
            
            # Build features for the ML model (simplified)
            features = {
                "failure_type": 0,
                "failure_injected": 0,
                "failure_detected": 0,
                "cpu_usage_cores": cpu,
                "memory_usage_bytes": memory,
                "disk_io_read_bytes": 0,
                "disk_io_write_bytes": 0,
                "network_rx_bytes": 0,
                "network_tx_bytes": 0,
                "oom_killed": 0,
                "restart_count": pod.status.container_statuses[0].restart_count if pod.status.container_statuses else 0,
                "latency_ms": 0,
                "container_ready": int(pod.status.container_statuses[0].ready) if pod.status.container_statuses else 0,
                "pod_scheduled": int(pod.status.phase == "Running"),
                "node_cpu_allocatable_cores": 2,      # Placeholder, fetch if needed
                "node_memory_allocatable_bytes": 4e9  # Placeholder, fetch if needed
            }
            
            result = predict_failure(features)
            if result:
                prob = result["probability_of_failure"]
                will_fail = result["will_fail_soon"]
                print(f"[INFO] Pod: {pod_name}, prob: {prob:.2f}, will_fail: {will_fail}")
                if will_fail and prob > FAILURE_THRESHOLD:
                    restart_pod(pod_name)
        
        time.sleep(SLEEP_INTERVAL)

# -----------------------------
# RUN AGENT
# -----------------------------
if __name__ == "__main__":
    print("[INFO] Starting Kubernetes crash monitoring agent...")
    monitor_pods()
