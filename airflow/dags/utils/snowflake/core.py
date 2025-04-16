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
    INSERT INTO SKILL_QA (SKILL, QUESTION, ANSWER)
    VALUES (%s, %s, %s)
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

