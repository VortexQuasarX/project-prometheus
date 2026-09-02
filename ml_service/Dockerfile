# ML inference microservice image (Python 3.11-slim, non-root)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY app/requirements.txt /app/app/requirements.txt
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir -r /app/app/requirements.txt \
    && /opt/venv/bin/pip install --no-cache-dir scikit-learn joblib

ENV PATH="/opt/venv/bin:$PATH"

COPY app/ /app/app/
COPY ml/ /app/ml/
COPY evals/ /app/evals/

RUN mkdir -p /app/ml/artifacts \
    && useradd --create-home --uid 1001 mluser \
    && chown -R mluser:mluser /app
USER mluser

EXPOSE 8100
CMD ["uvicorn", "ml_service.main:app", "--host", "0.0.0.0", "--port", "8100"]
