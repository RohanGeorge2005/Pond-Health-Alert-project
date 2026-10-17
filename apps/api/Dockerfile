FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (including OpenCV dependencies)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY apps/api /app/apps/api
COPY config /app/config
COPY ml /app/ml
COPY docs /app/docs

RUN pip install --no-cache-dir -e /app/apps/api

EXPOSE 8000

CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
