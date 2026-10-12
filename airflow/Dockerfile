# Custom Airflow image: official Airflow + the tools our pipeline needs
FROM apache/airflow:3.1.0-python3.12

# Libraries used by our generator and ingestion scripts.
# Pinning apache-airflow stops pip from upgrading Airflow's own dependencies.
# (psycopg2 already comes with the official image.)
RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" faker python-dotenv

# dbt in its own virtual environment, isolated from Airflow's libraries
RUN python -m venv /opt/airflow/dbt_venv \
 && /opt/airflow/dbt_venv/bin/pip install --no-cache-dir dbt-postgres