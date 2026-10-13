# One image holds Airflow, our Python packages, our code and the embedding model.
# Every Airflow service in docker-compose.yaml runs this same image.
FROM apache/airflow:3.3.2-python3.13

# Pinning apache-airflow keeps pip from changing the Airflow version in the base image.
RUN pip install --no-cache-dir \
    "apache-airflow==3.3.2" \
    duckdb==1.5.6 \
    lancedb==0.40.0 \
    fastembed==0.9.0 \
    anthropic==1.13.0

# Download the embedding model while building, so no task has to fetch it at run time.
ENV FASTEMBED_CACHE_PATH=/opt/airflow/model-cache
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5')"

# The code is part of the image: a new version of the pipeline means a new image.
COPY dags/ /opt/airflow/dags/
COPY listings/ /opt/airflow/app/listings/
COPY sources/ /opt/airflow/app/sources/
COPY rag/ /opt/airflow/app/rag/
COPY sql/ /opt/airflow/app/sql/
COPY data/eval/ /opt/airflow/app/data/eval/
COPY main.py /opt/airflow/app/main.py

ENV PYTHONPATH=/opt/airflow/app
# Data does not live in the image. This folder is replaced by a volume when the container runs.
ENV LISTINGS_DATA_DIR=/opt/airflow/pipeline-data
RUN mkdir -p /opt/airflow/pipeline-data
