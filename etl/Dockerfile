FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

COPY data/scripts/requirements.txt /app/data/scripts/requirements.txt
COPY ml/requirements.txt /app/ml/requirements.txt

RUN pip install --no-cache-dir \
    -r data/scripts/requirements.txt \
    -r ml/requirements.txt \
    pyyaml

COPY data/ /app/data/
COPY etl/ /app/etl/
COPY ml/ /app/ml/
COPY pyproject.toml /app/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "etl.pipelines.seed"]
