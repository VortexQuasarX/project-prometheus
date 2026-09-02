# MLOps

## Lifecycle (VERIFIED locally)

1. **Dataset**: distilled from the deterministic router (48 rows, augmentation),
   8 hand-crafted features (`app/ml/dataset.py`).
2. **Training**: `python -m app.ml.train` — LogisticRegression, measured
   accuracy/precision/recall/F1 in `ml/artifacts/metrics.json` (VERIFIED).
3. **Experiment tracking**: MLflow sqlite backend (`ml/mlruns/mlflow.db`),
   params/metrics/artifacts logged (VERIFIED — test_mlflow_run_logged).
4. **Drift detection**: PSI per feature, threshold 0.2
   (`app/ml/drift.py`, VERIFIED: flags real shift, no false positive).
5. **Safe retraining**: `app/ml/retrain.py` — candidate must beat production
   by ≥2pp accuracy to promote; history is append-only
   (`ml/artifacts/model_history.json`); rollback artifact kept (VERIFIED).
6. **Serving**: `ml_service/main.py` — versioned `/predict`, `/predict/batch`,
   `/ready`, `/metrics` (VERIFIED via app; live serving on a cluster NOT VERIFIED).
7. **Promotion rules**: candidate → (accuracy gate) → production alias;
   deployment into the gateway is a config flip once the inference service is
   wired into the router (roadmap).

## NOT VERIFIED / FUTURE

- Airflow-scheduled retraining (DAGs shipped in `ml/airflow_dags/`)
- Real Bedrock/OpenAI inference (needs credentials)
- Distributed training / GPU (roadmap V3)
