# Kubernetes

Manifests: `infra/k8s/` — api.yaml (Deployment+Service+HPA 2→10 @70% CPU),
ml-inference.yaml (Deployment+Service+HPA 2→8 @65% CPU), config.yaml
(ConfigMap+Secret placeholders+NGINX Ingress with TLS).

## Verification status

- **VERIFIED (structural)**: YAML parses; every document has apiVersion/kind/
  metadata; probes, resources, HPA present.
- **NOT VERIFIED (no cluster on host)**: `kubectl apply`, HPA autoscaling
  behavior under load, live probes.

## Deploy (needs a cluster)

```bash
kubectl create secret generic prometheus-secrets \
  --from-literal=OPENAI_API_KEY=... --from-literal=ADMIN_API_KEY=...
kubectl apply -f infra/k8s/
```

Kafka + PostgreSQL are external (MSK/Aurora in AWS; or in-cluster charts) —
wired via the ConfigMap `DATABASE_URL` / `KAFKA_BOOTSTRAP_SERVERS`.
