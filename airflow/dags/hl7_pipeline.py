"""
Daily HL7 clinical data pipeline.

generate -> ingest (raw / Bronze) -> dbt build (staging + marts, with tests)
"""

from datetime import datetime, timedelta

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG

PROJECT_DIR = "/opt/project"
DBT_BIN = "/opt/airflow/dbt_venv/bin/dbt"

default_args = {
    "owner": "data-engineering",
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}

with DAG(
    dag_id="hl7_clinical_pipeline",
    description="Daily ELT: synthetic HL7 v2 messages -> PostgreSQL -> dbt",
    schedule="@daily",
    start_date=datetime(2026, 10, 1),
    catchup=False,
    default_args=default_args,
    tags=["hl7", "healthcare", "elt"],
) as dag:

    generate = BashOperator(
        task_id="generate_hl7_messages",
        bash_command=f"cd {PROJECT_DIR} && python src/generate_hl7.py",
    )

    ingest = BashOperator(
        task_id="ingest_raw_layer",
        bash_command=f"cd {PROJECT_DIR} && python src/ingest_hl7.py",
    )

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=f"cd {PROJECT_DIR}/dbt && {DBT_BIN} build",
    )

    generate >> ingest >> dbt_build