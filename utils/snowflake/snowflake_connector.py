import snowflake.connector as sf
from typing import List, Dict, Any
from dotenv import load_dotenv
import os
import json
import pandas as pd

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


def get_this_column(user_email, columns):
    if isinstance(columns, str):
        columns_str = columns
    elif isinstance(columns, list):
        columns_str = ", ".join(columns)
    else:
        raise ValueError("columns must be a string or list of strings")

    conn = sf_client()
    cursor = conn.cursor()
    select_query = f"SELECT {columns_str} FROM user_artifacts WHERE user_email = %s"
    try:
        cursor.execute(select_query, (user_email,))
        result = cursor.fetchone()
        cursor.close()
        if result is None:
            return None

        if isinstance(columns, str):
            return result[0]
        else:
            return dict(zip(columns, result))
    except Exception as e :
        return str(e)



def get_this_column_qa(user_email, columns):
    if isinstance(columns, str):
        columns_str = columns
    elif isinstance(columns, list):
        columns_str = ", ".join(columns)
    else:
        raise ValueError("columns must be a string or list of strings")

    conn = sf_client()
    cursor = conn.cursor()
    select_query = f"SELECT {columns_str} FROM qa_pipeline_status WHERE user_email = %s"
    cursor.execute(select_query, (user_email,))
    result = cursor.fetchone()
    cursor.close()
    if result is None:
        return None

    if isinstance(columns, str):
        return result[0]
    else:
        return dict(zip(columns, result))


def update_this_column(user_email, column, data):
  conn = sf_client()
  cursor = conn.cursor()
  update_query = f"""
      UPDATE user_artifacts
      SET {column} = %s
      WHERE user_email = %s
  """
  cursor.execute(update_query, (data, user_email))
  cursor.close()


  
def update_this_column_qa( column, data, dag_run_id):
  conn = sf_client()
  cursor = conn.cursor()
  update_query = f"""
      UPDATE qa_pipeline_status
      SET {column} = %s
      WHERE dag_run_id = %s
  """
  cursor.execute(update_query, (data, dag_run_id))
  cursor.close()


def request_to_signup(user_email, full_name, profession):
    conn = sf_client()
    cursor = conn.cursor()
    cnt = cursor.execute("select count(*) from signup_requests where user_email = %s", (user_email)).fetchone()[0]
    if cnt==0:
        status = cursor.execute("insert into signup_requests(full_name, user_email, profession, status) values(%s, %s, %s, %s)", (full_name, user_email, profession, 'REQUEST')).fetchone()[0]
    else:
        status=0
    cursor.close()
    return status    


def pipeline_status(user_email):
    conn = sf_client()
    cursor = conn.cursor()
    df = cursor.execute("select DAG_RUN_ID, STATUS from qa_pipeline_status where user_email = %s", (user_email)).fetch_pandas_all()
    if df.empty:
       return []
    cursor.close()
    return df.to_dict(orient='records')


def get_qa(dag_run_id):
    conn = sf_client()
    cursor = conn.cursor()
    data = cursor.execute("select qa_data from qa_pipeline_status where dag_run_id = %s", (dag_run_id)).fetchone()[0]
    if not data:
        return []
    data = json.loads(data)
    cursor.close()
    return [{"ID": item["ID"], "QUESTION": item["QUESTION"] } for item in data]


def map_user_answers(answers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not answers:
        return []
 
    ids = [pair["id"] for pair in answers]
 
    query = f"""
        SELECT ID, QUESTION, ANSWER
        FROM skill_qa
        WHERE ID IN ({','.join(['%s'] * len(ids))})
    """
 
    with sf_client() as conn:
        df = conn.cursor().execute(query, ids).fetch_pandas_all()
 
    lookup = {
        row["ID"]: {"question": row["QUESTION"], "actual_answer": row["ANSWER"]}
        for _, row in df.iterrows()
    }
 
    return [
        {
            "id": pair["id"],
            "user_answer": pair["user_answer"],
            **lookup.get(pair["id"], {"question": None, "actual_answer": None})
        }
        for pair in answers
    ]


