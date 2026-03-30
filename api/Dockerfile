FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

COPY api/requirements.txt /app/api/requirements.txt
COPY data/scripts/requirements.txt /app/data/scripts/requirements.txt
COPY ml/requirements.txt /app/ml/requirements.txt

RUN pip install --no-cache-dir \
    -r api/requirements.txt \
    -r data/scripts/requirements.txt \
    -r ml/requirements.txt \
    pyyaml

COPY api/ /app/api/
COPY data/ /app/data/
COPY ml/ /app/ml/
COPY etl/ /app/etl/
COPY pyproject.toml /app/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "api.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
