from airflow import DAG
from airflow.decorators import task
from airflow.operators.python import get_current_context
from datetime import datetime
from utils.snowflake.core import write_qa, is_skill_exist_via
from utils.s3.core import get_s3_client, write_markdown_to_s3
from utils.langgraph.pipeline import lang_qa_pipeline
from uuid import uuid4
from dotenv import load_dotenv
load_dotenv()

with DAG(
    dag_id='qa_pipeline',
    start_date=datetime(2023, 1, 1),
    schedule_interval=None,
) as dag:

    @task
    def extract_links():
        context = get_current_context()
        links_conf = context["dag_run"].conf
        return links_conf

    @task
    def qa_using_llm(state):
        links = state['qa_data']
        for skill, _links in links.items():
            skill = skill.lower()
            print(f'================== {skill} ==================')
            for link in _links:
                skill_exists = is_skill_exist_via('SOURCE', link)
                if skill_exists:
                    print(f"{skill} exists in the form of {link} in sf, hence skipping")
                if not is_skill_exist_via('SOURCE', link):
                    input_state = {
                        "skill" : skill,
                        "insert_data":[],
                        "current_link": link,
                        "exclude_domains": [],
                        "retry_count": 0  # Start with 0 retries
                    }
                    state = lang_qa_pipeline().invoke(input_state)
                    insert_data = state['insert_data']
                    if insert_data:
                        row_count = write_qa(insert_data)
                        write_markdown_to_s3(get_s3_client(), state['report_data'], f"validations/{skill}/{uuid4()}.md")
                        print("{} -> loaded {} rows".format(skill, row_count))
                    else:
                        print("Agent tried to look for alternatives, unfortunately the data from web, did not meet the platform standards")
        return None
    
    state = extract_links()
    qa_using_llm(state) 
    
    