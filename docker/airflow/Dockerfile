FROM apache/airflow:2.9.3-python3.11

USER root
RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /opt/project/requirements.txt

USER airflow
RUN pip install --no-cache-dir -r /opt/project/requirements.txt
