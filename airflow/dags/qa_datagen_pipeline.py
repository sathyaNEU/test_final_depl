from airflow import DAG
from airflow.decorators import task
from airflow.operators.python import get_current_context
from datetime import datetime
from utils.firecrawl.core import scrape_this_site
from utils.snowflake.core import write_qa, is_skill_exist_via
from utils.llm.core import generate_qa
from utils.s3.core import get_s3_client, write_markdown_to_s3
from utils.haystack.pipeline import doc_splitter
from haystack_integrations.components.rankers.cohere import CohereRanker
from haystack.dataclasses.byte_stream import ByteStream
import time
from uuid import uuid4
import random
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
    def qa_using_llm(links):
        _doc_splitter = doc_splitter()
        # core validation functionality using cohere ranker
        ranker = CohereRanker()
        for skill, _links in links.items():
            skill = skill.lower()
            for link in _links:
                if not is_skill_exist_via('SOURCE', link):
                    site_as_md = scrape_this_site(link)
                    md_stream = ByteStream(data=site_as_md.encode("utf-8"), mime_type="text/markdown")
                    docs = _doc_splitter.run({"md_file_converter": {"sources": [md_stream]}})['splitter']['documents']
                    qa = generate_qa(site_as_md)
                    if isinstance(qa, int):
                        continue
                    #batch insert
                    markdown_str =""
                    insert_data = []
                    for row in qa:
                        q,a = row["question"], row["answer"]
                        doc = ranker.run(query=q+a, documents=docs, top_k=1)['documents'][0]
                        if doc.score > 0.96:
                            insert_data.append((skill, q, a, link))
                        markdown_str += f"### Question:\n{q}\n\n"
                        markdown_str += f"**Answer:**\n{a}\n\n"
                        markdown_str += f"**Context:**\n{doc.content}\n\n"
                        markdown_str += f"**Score:** `{doc.score}`\n\n"
                        markdown_str += "---\n\n"
                        delay = random.uniform(4, 10)
                        print(f"sleeping {delay} to avoid rate limits")
                        time.sleep(delay)
                    row_count = write_qa(insert_data)
                    write_markdown_to_s3(get_s3_client(), markdown_str, f"validations/{skill}/{uuid4()}.md")
                    print("{} -> loaded {} rows".format(skill, row_count))
    links = extract_links()
    qa_using_llm(links) 
    
    