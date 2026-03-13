FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY . /app
RUN pip install --no-cache-dir .

# Run as non-root in container runtime
RUN useradd -m -u 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["uvicorn", "grantflow.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
