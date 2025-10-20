# Kubernetes Crash Monitoring Agent

This repository contains a **Kubernetes Crash Monitoring Agent** that predicts potential pod crashes in real-time using machine learning. The agent collects metrics from pods and nodes, feeds them to a trained ML model, and provides crash predictions via a FastAPI REST API.

---

## **Project Structure**

k8s-crash-monitor/
├── agent/
│ ├── app.py # FastAPI app serving predictions
│ ├── requirements.txt # Python dependencies
│ └── agent.py # Optional background logic for monitoring
├── model/
│ └── crash_predictor.pkl # Pre-trained ML model
├── ml/
│ └── train_model.py # Script to train the ML model
├── k8s-manifests/
│ ├── crash-predictor-deployment.yaml
│ ├── crash-predictor-service.yaml
│ ├── stress-pod.yaml
│ └── metrics-server.yaml
├── Dockerfile # Containerizes FastAPI app + model
├── .gitignore
├── LICENSE
└── README.md


---

## **Prerequisites**

Before running the project, ensure you have:

- [Docker](https://docs.docker.com/get-docker/) installed
- [kubectl](https://kubernetes.io/docs/tasks/tools/) installed
- [Minikube](https://minikube.sigs.k8s.io/docs/start/) or any Kubernetes cluster running
- Python 3.11+ (for local testing or model training)
- `pip` installed

---

## **Step 1: Train the Model (Optional)**

If you want to retrain the model:

```bash
cd ml
python train_model.py
Step 2: Build Docker Image

From the root directory:

docker build -t crash-predictor-agent .


This builds the container with FastAPI and the ML model.

Make sure app.py and requirements.txt are in agent/.

Exposes port 8000 for the FastAPI server.

Step 3: Run Locally (Optional)

To test the agent locally:

docker run -p 8000:8000 crash-predictor-agent


The FastAPI server will be available at http://localhost:8000.

Test it using curl:

curl -X POST http://localhost:8000/predict \
-H "Content-Type: application/json" \
-d '{"cpu_usage_cores":0.5,"memory_usage_bytes":1024}'

Step 4: Deploy to Kubernetes
4.1 Start Minikube (if not running):
minikube start

4.2 Apply Kubernetes manifests:
kubectl apply -f k8s-manifests/crash-predictor-deployment.yaml
kubectl apply -f k8s-manifests/crash-predictor-service.yaml
kubectl apply -f k8s-manifests/metrics-server.yaml

4.3 Check pods:
kubectl get pods -n default
kubectl get pods -n kube-system


Ensure the crash-predictor pod is running.

Ensure the metrics-server pod is running for pod metrics.

Step 5: Port Forward to Access the API
kubectl port-forward service/crash-predictor-service 8000:80


Access FastAPI at http://localhost:8000.

Use curl or Postman to test predictions:

curl -X POST http://localhost:8000/predict \
-H "Content-Type: application/json" \
-d '{"cpu_usage_cores":0.5,"memory_usage_bytes":1024}'

Step 6: Test Crash Prediction
You can simulate high CPU/memory usage with a stress pod:
kubectl apply -f k8s-manifests/stress-pod.yaml
Check logs of the agent for predicted crashes.

Example log output:

[INFO] Starting Kubernetes crash monitoring agent...
[INFO] Crash predicted for pod stress-pod

Step 7: Clean Up

After testing:

kubectl delete -f k8s-manifests/stress-pod.yaml
kubectl delete -f k8s-manifests/crash-predictor-deployment.yaml
kubectl delete -f k8s-manifests/crash-predictor-service.yaml
kubectl delete -f k8s-manifests/metrics-server.yaml

Notes

Make sure the metrics-server is working correctly, or the agent will not receive metrics.

If running on Windows PowerShell, use Invoke-WebRequest instead of curl.

The agent currently expects CPU in cores and memory in bytes.
