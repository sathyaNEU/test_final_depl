from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.decorators import task, branch_task
from airflow.operators.python import get_current_context
from datetime import datetime
from utils.snowflake.core import write_qa, is_skill_exist_via, distinct_skills, random_n_qa, bind_qa
from utils.s3.core import get_s3_client, write_markdown_to_s3
from utils.langgraph.pipeline import lang_qa_pipeline
from utils.tavily.core import web_api
from uuid import uuid4
from dotenv import load_dotenv
load_dotenv()

# this dag will always accept params in this format:
# { user_email:str
#   skills: list
#}

with DAG(
    dag_id='qa_pipeline',
    start_date=datetime(2023, 1, 1),
    schedule_interval=None,
) as dag:

    @task
    def extract_links():
        context = get_current_context()
        state = context["dag_run"].conf
        return state

    @task
    def qa_using_llm(state):
        skills = state['skills']
        # filter skills not in snowflake
        _distinct_skills = distinct_skills(skills)
        _distinct_skills = [skill_item['SKILLS'] for skill_item in _distinct_skills]
        skills_to_process = list(set(skills) - set(_distinct_skills))
        links = {skill: web_api(skill) for skill in skills_to_process}
        print('tavily output', links)
        for skill, _links in links.items():
            skill = skill.lower()
            print(f'================== {skill} ==================')
            for link in _links:
                # print('checking this link in snowflake', link)
                mode = state.get("mode", "").lower()
                print('mode : ', mode)
                skill_exists = is_skill_exist_via('SKILL', skill) if mode=='import_qa' else is_skill_exist_via('SOURCE', link)
                if skill_exists:
                    print(f"skipping agentic pipeline, since skill exist")
                if not skill_exists:
                    input_state = {
                        "skill" : skill,
                        "insert_data":[],
                        "current_link": link,
                        "exclude_domains": [],
                        "retry_count": 0  # Start with 0 retries
                    }
                    lang_state = lang_qa_pipeline().invoke(input_state)
                    insert_data = lang_state['insert_data']
                    if insert_data:
                        row_count = write_qa(insert_data)
                        write_markdown_to_s3(get_s3_client(), lang_state['report_data'], f"validations/{skill}/{uuid4()}.md")
                        print("{} -> loaded {} rows".format(skill, row_count))
                    else:
                        print("Agent tried to look for alternatives, unfortunately the data from web, did not meet the platform standards")
        return state
    
    @branch_task
    def route_based_on_mode(state):
        mode = state["mode"]
        print("selected mode :", mode)
        if mode == "import_qa":
            return "gf_task"
        else:
            return "end_task"  
        
    @task(task_id="gf_task")
    def gf_task(state):
        skills = state['skills']  
        prep_qa = random_n_qa(skills=skills)
        bind_qa(state["dag_run_id"],prep_qa)
        
    end_task = EmptyOperator(task_id="end_task")

    state = extract_links()
    intm_state = qa_using_llm(state)
    mode_branch = route_based_on_mode(intm_state)
    mode_branch >> [gf_task(intm_state), end_task]
    
    