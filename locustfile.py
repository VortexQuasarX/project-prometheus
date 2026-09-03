from locust import HttpUser, task, between
import json

class PrometheusUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task
    def chat_request(self):
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": "prometheus-demo-admin-key"
        }
        payload = {
            "query": "What is AI cost governance?"
        }
        with self.client.post("/api/v1/chat", headers=headers, json=payload, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                response.success()  # 429 is a SUCCESSFUL rate limit
            else:
                response.failure(f"Failed with status {response.status_code}")
