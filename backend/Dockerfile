# GeneGauge PGC backend — FastAPI served by uvicorn.
# Built for Render's Docker web service (not a serverless function).
FROM python:3.12-slim

# libgomp1 is needed by scipy/duckdb at runtime; matplotlib runs headless (Agg backend).
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg \
    GENEGAUGE_DEMO_MODE=1

EXPOSE 8000

# Render injects $PORT; default to 8000 for local `docker run`.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
