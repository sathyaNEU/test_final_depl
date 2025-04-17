import snowflake.connector as sf
import os

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

def upsert_qa_pipeline_status(user_email, dag_id, dag_run_id, status):
    conn = sf_client()
    cursor = conn.cursor()
    select_query = """
        SELECT COUNT(*) AS count FROM QA_PIPELINE_STATUS WHERE DAG_RUN_ID = %s
    """
    insert_query = """
        INSERT INTO QA_PIPELINE_STATUS (USER_EMAIL, DAG_ID, DAG_RUN_ID, STATUS)
        VALUES (%s, %s, %s, %s)
    """
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
            cursor.execute(insert_query, (user_email, dag_id, dag_run_id, status))
    except Exception as e:
        print(f"Error updating pipeline status: {str(e)}")
    finally:
        cursor.close()
        conn.close()

