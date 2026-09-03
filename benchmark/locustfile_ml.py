import random
from locust import HttpUser, task, between, events

class MLInferenceUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task(3)
    def predict_simple(self):
        self.client.post(
            "/predict",
            json={"text": "hello what is your name?"},
            name="/predict (simple)"
        )

    @task(1)
    def predict_complex(self):
        self.client.post(
            "/predict",
            json={"text": "Write a detailed financial analysis of the upcoming merger between Corp A and Corp B including cost synergy estimates."},
            name="/predict (complex)"
        )

    @task(2)
    def predict_batch(self):
        texts = [
            "how to reset password",
            "explain quantum physics",
            "give me a recipe for bread",
            "analyze this python code for bugs"
        ]
        self.client.post(
            "/predict/batch",
            json={"texts": random.sample(texts, 3)},
            name="/predict/batch"
        )
