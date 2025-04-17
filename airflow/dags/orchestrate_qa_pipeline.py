from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow import DAG
from airflow.decorators import task
from airflow.operators.python import get_current_context
from datetime import datetime
from airflow.utils.state import State
from airflow.models import DagRun
from airflow.utils.session import provide_session
from utils.snowflake.core import upsert_qa_pipeline_status
from uuid import uuid4
from dotenv import load_dotenv
import json  # Add this import
load_dotenv()

with DAG(
    dag_id="orchestrate_qa_pipeline",
    start_date=datetime(2024, 1, 1),
    schedule_interval=None,
    catchup=False,
    tags=["trigger"],
) as dag:

    @task
    def extract_params():
        context = get_current_context()
        return context["dag_run"].conf

    @task
    def sf_job_update_queued(state):
        dag_run_id = str(uuid4())
        state["dag_run_id"] = dag_run_id
        upsert_qa_pipeline_status(state['user_email'], 'qa_pipeline', dag_run_id, 'queued')
        return state

    @task
    def prepare_for_trigger(state):
        # Ensure state is JSON serializable
        return state

    # Define the TriggerDagRunOperator with proper JSON string for conf
    trigger_qa_pipeline = TriggerDagRunOperator(
        task_id="trigger_qa_pipeline",
        trigger_dag_id="qa_pipeline",
        trigger_run_id="{{ ti.xcom_pull(task_ids='prepare_for_trigger')['dag_run_id'] }}",
        wait_for_completion=True,
        # Properly serialize the conf as JSON
        conf="{{ ti.xcom_pull(task_ids='prepare_for_trigger') | tojson }}",
    )

    @task
    def sf_job_update_completed(state):
        @provide_session
        def get_dag_run_status(dag_id, run_id, session=None):
            dag_run = session.query(DagRun).filter(
                DagRun.dag_id == dag_id,
                DagRun.run_id == run_id
            ).one_or_none()
            
            if dag_run:
                return dag_run.state
            return 'unknown'
        
        status = get_dag_run_status('qa_pipeline', state['dag_run_id'])
        
        final_status = 'completed'
        if status == State.SUCCESS:
            final_status = 'completed'
        elif status == State.FAILED:
            final_status = 'failed'
        else:
            final_status = 'unknown'
        
        upsert_qa_pipeline_status(state['user_email'], 'qa_pipeline', state['dag_run_id'], final_status)
        return state

    # Chain tasks
    state = extract_params()
    updated_state = sf_job_update_queued(state)
    prepared = prepare_for_trigger(updated_state)
    prepared >> trigger_qa_pipeline
    done = sf_job_update_completed(prepared)
    trigger_qa_pipeline >> done