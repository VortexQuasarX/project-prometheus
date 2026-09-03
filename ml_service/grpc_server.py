import logging
import time
from concurrent import futures

import grpc

from app.ml.train import predict_complexity
from ml_service.proto import inference_pb2, inference_pb2_grpc

logger = logging.getLogger("ml_service.grpc")

class InferenceServiceServicer(inference_pb2_grpc.InferenceServiceServicer):
    def Predict(self, request, context):
        # We need to import the model state dynamically or use a singleton,
        # but in ml_service/main.py, load_model() sets the global _model.
        import ml_service.main as main_svc
        if main_svc._model is None:
            context.abort(grpc.StatusCode.UNAVAILABLE, "model not loaded")

        started = time.perf_counter()
        result = predict_complexity(main_svc._model, request.text)
        latency = (time.perf_counter() - started) * 1000
        return inference_pb2.PredictResponse(
            complexity_class=result["complexity_class"],
            confidence=result["confidence"],
            latency_ms=latency,
            model_version=main_svc.MODEL_VERSION
        )

    def PredictBatch(self, request, context):
        import ml_service.main as main_svc
        if main_svc._model is None:
            context.abort(grpc.StatusCode.UNAVAILABLE, "model not loaded")

        started = time.perf_counter()
        results = [predict_complexity(main_svc._model, t) for t in request.texts]
        latency = (time.perf_counter() - started) * 1000

        predictions = [
            inference_pb2.PredictResponse(
                complexity_class=r["complexity_class"],
                confidence=r["confidence"],
                latency_ms=0.0,
                model_version=main_svc.MODEL_VERSION
            ) for r in results
        ]

        return inference_pb2.BatchPredictResponse(
            predictions=predictions,
            batch_size=len(request.texts),
            latency_ms=latency
        )

def serve():
    import ml_service.main as main_svc
    try:
        main_svc.load_model()
    except Exception as e:
        logger.warning(f"Failed to load model on startup: {e}")

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    inference_pb2_grpc.add_InferenceServiceServicer_to_server(
        InferenceServiceServicer(), server
    )
    server.add_insecure_port("[::]:50051")
    logger.info("Starting gRPC server on port 50051")
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    serve()
