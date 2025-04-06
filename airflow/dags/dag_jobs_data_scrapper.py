from airflow.operators.python import PythonOperator
from airflow import DAG
from job_scrapper.job_link_scrapper import * 



with DAG(
    dag_id= "job_scrapper",
    description="dag for scraping job links and job deatils",
     start_date="45 0 0 0 0",
    schedule_interval="@daily"

) as dag :

    roles=["data Engineer","data scientist","software engineer"]
    scrape_job_links = PythonOperator (
        task_id = "scrape_job_links",
        python_callable= scrape_linkedin_jobs,
        params={
            "roles" : roles,
            "options" :{
                "time_posted": 1800,  
                "location": "United States"
             }
        }
    )
