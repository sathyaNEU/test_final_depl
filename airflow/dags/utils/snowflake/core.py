import snowflake.connector as sf
import pandas as pd
import os
import json

def sf_client():
    conn = sf.connect(
      user=os.getenv('SF_USER'),
      password=os.getenv('SF_PASSWORD'),
      account=os.getenv('SF_ACCOUNT'),
      warehouse="BOTFOLIO_WH",
      database="BOTFOLIO_DB",
      schema="APP",
      role="BOTFOLIO"
    )
    return conn

  
def write_qa(insert_data):
    conn = sf_client()
    cursor = conn.cursor()

    insert_query = """
    INSERT INTO SKILL_QA (SKILL, QUESTION, ANSWER, SOURCE)
    VALUES (%s, %s, %s, %s)
    """
    try:
        cursor.executemany(insert_query, insert_data)
        rows_inserted = cursor.rowcount
    except Exception as e:
        rows_inserted = 0
    finally:
        cursor.close()
        conn.close()
    return rows_inserted

def is_skill_exist_via(column, data):
    conn = sf_client()
    cursor = conn.cursor()
    select_query = f"select count(ID) from skill_qa WHERE {column} = %s"
    data = cursor.execute(select_query, (data)).fetchone()[0]
    cursor.close()
    return data>0

def distinct_skills(skills):
    conn = sf_client()
    cursor = conn.cursor()
    skills = [skill.lower() for skill in skills]
    # Build a list of placeholders (%s) for the SQL query
    placeholders = ','.join(['%s'] * len(skills))
    select_query = f"""
    SELECT DISTINCT SKILL AS SKILLS FROM SKILL_QA WHERE lower(SKILL) IN ({placeholders})
    """
    try:
        df = cursor.execute(select_query, tuple(skills)).fetch_pandas_all()
    except Exception as e:
        print(str(e))
        df = pd.DataFrame([], columns=['SKILLS'])
    finally:
        cursor.close()
        conn.close()
    return df.to_dict(orient='records')  

def upsert_qa_pipeline_status(user_email, skills, dag_id, dag_run_id, status, job_url=None):
    conn = sf_client()
    cursor = conn.cursor()
    skills_array = json.dumps(skills)
    select_query = """
        SELECT COUNT(*) AS count FROM QA_PIPELINE_STATUS WHERE DAG_RUN_ID = %s
    """
    insert_query = f"""
        INSERT INTO QA_PIPELINE_STATUS (USER_EMAIL,SKILLS, DAG_ID, DAG_RUN_ID, STATUS, JOB_URL, STARTED_AT)
        SELECT %s, PARSE_JSON(%s), %s, %s, %s, %s, CURRENT_TIMESTAMP
    """
    if status in ('success', 'failed', 'unknown'):
        update_query = """
            UPDATE QA_PIPELINE_STATUS SET STATUS = %s, ENDED_AT = CURRENT_TIMESTAMP
            WHERE DAG_RUN_ID = %s
        """
    else:
        update_query = """
            UPDATE QA_PIPELINE_STATUS SET STATUS = %s
            WHERE DAG_RUN_ID = %s
        """
    try:
        count_df = cursor.execute(select_query, (dag_run_id,)).fetch_pandas_all()
        record_exists = count_df.iloc[0]['COUNT'] > 0
        if record_exists:
            cursor.execute(update_query, (status, dag_run_id))
        else:
            cursor.execute(insert_query, (user_email, skills_array, dag_id, dag_run_id, status, job_url))
    except Exception as e:
        print(f"Error updating pipeline status: {str(e)}")
    finally:
        cursor.close()
        conn.close()

def random_n_qa(skills, n=10):
    conn = sf_client()
    cursor = conn.cursor()
    skills = [skill.lower() for skill in skills]
    # Build a list of placeholders (%s) for the SQL query
    placeholders = ','.join(['%s'] * len(skills))
    select_query = f"""
    SELECT * FROM (
    SELECT * FROM SKILL_QA WHERE lower(SKILL) IN ({placeholders})
    ) SAMPLE (%s ROWS)
    """
    try:
        df = cursor.execute(select_query, (*skills, n)).fetch_pandas_all()
    except Exception as e:
        print(str(e))
        df = pd.DataFrame([], columns=['ID', 'SKILL', 'QUESTION', 'ANSWER', 'SOURCE'])
    finally:
        cursor.close()
        conn.close()
    return df.to_dict(orient='records')  

def bind_qa(dag_run_id, qa_data):
    try:
        conn = sf_client()
        cursor = conn.cursor()
        jsonable_qa_data = json.dumps(qa_data)
        update_query = f"""
            UPDATE QA_PIPELINE_STATUS SET QA_DATA = PARSE_JSON(%s)
            WHERE DAG_RUN_ID = %s
        """
        cursor.execute(update_query, (jsonable_qa_data, dag_run_id))
        cursor.close()
        conn.close()
        return True
    except:
        return False