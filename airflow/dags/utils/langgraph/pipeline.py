from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from mistralai import Mistral
from mistralai.models import SDKError
import time
import random
import os
from utils.tavily.core import web_api
from utils.firecrawl.core import scrape_this_site
from utils.haystack.pipeline import doc_splitter
from utils.llm.core import generate_qa as qa_llm
from haystack_integrations.components.rankers.cohere import CohereRanker
from haystack.dataclasses.byte_stream import ByteStream
from dotenv import load_dotenv
load_dotenv()

# Define shared state
class State(TypedDict):
    context: str
    skill: str
    is_valid: bool
    qa_pairs: list
    current_link: str  # The current URL of the content being processed
    exclude_domains: list  # List of domains to exclude when retrying
    retry_count: int  # Track the number of retries
    insert_data: list # sf ready insert data
    report_data: str

def scraper(state:State):
    print(f"================= SCRAPE {state['current_link']}=================")
    link = state['current_link']
    if link:
        return {'context':scrape_this_site(state['current_link'])}
    return {'context':""}

# Validate the context
def validate_context(state: State):
    print("================= VALIDATE CONTEXT STARTED =================")
    prompt = (
        f"You're given this interview context:\n\n{state['context']}\n\n"
        "Without generating the questions, just answer Yes or No: Can at least 10 relevant interview questions "
        "be made from this content?"
    )
    retries = 2
    delay = 61 
    client = Mistral(api_key=os.getenv('MISTRAL_API_KEY'))
    for attempt in range(retries):
        try:
            response = client.chat.complete(
                model="mistral-small-latest",
                messages=[{"role": "user", "content": prompt}]
            )
            answer = response.choices[0].message.content.strip().lower()
            return {"is_valid": "yes" in answer}
        
        except SDKError as e:
            if e.status_code == 429:
                print(f"Rate limited (429). Retry {attempt+1}/{retries} after {delay} seconds...")
                time.sleep(delay)
                delay *= 2  # optional: exponential backoff
            else:
                print(f"SDKError: {e.status_code} - {e.message}")
                break
        except Exception as e:
            print(f"Unexpected error: {e}")
            break
    return {"is_valid": False}

# Router node to check if context is valid or not
def context_check_router(state: State):
    print("================= ROUTING CHECK =================")
    if state["retry_count"] >= 1:
        # Stop the process if retry count is 1 (end without QA generation)
        return "End"
    return "Valid" if state["is_valid"] else "Invalid"

# Fetch a new link from web API if the context is invalid
def fetch_alternative_link(state: State):
    print("================= CHOSEN ROUTE : ALTERNATE LINK =================")
    # Increase retry count after each invalid context
    skill = state['skill']
    exclude_domains = state.get("exclude_domains", [])
    exclude_domains.append(state.get("current_link", ""))  # Add the current link to exclude list
    
    # Call the web API to get a new link
    new_links = web_api(skill, exclude_domains=exclude_domains).get(skill, [])
    new_link = new_links[0] if new_links else None  # Get the first URL from the response
    
    if not new_link:
        print("No new links found.")
        return {"context": "", "current_link": "", "exclude_domains": exclude_domains, "retry_count": state["retry_count"]+1}

    return {
        "current_link": new_link,
        "exclude_domains": exclude_domains,
        "retry_count": state["retry_count"] + 1  # Increment retry count
    }

# Generate QAs from the provided context
def generate_qa(state: State):
    print("================= QA GENERATION =================")
    try:
        return {"qa_pairs": qa_llm(state['context'])} 
    except Exception as e:
        print("Error reading QA file:", e)
        return {"qa_pairs": []}

def validate_qa(state: State):
    print("================= FINAL VALIDATION =================")
    _doc_splitter = doc_splitter()
    # core validation functionality using cohere ranker
    ranker = CohereRanker()
    site_as_md = state['context']
    qa = state['qa_pairs']
    md_stream = ByteStream(data=site_as_md.encode("utf-8"), mime_type="text/markdown")
    docs = _doc_splitter.run({"md_file_converter": {"sources": [md_stream]}})['splitter']['documents']
    skill = state['skill']
    link = state['current_link']
    if isinstance(qa, int):
        {"insert_data": []}
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
        delay = random.uniform(10, 13)
        print(f"sleeping {delay} to avoid rate limits")
        time.sleep(delay)
    return {'insert_data':insert_data, 'report_data': markdown_str}

# Build LangGraph
def lang_qa_pipeline():
    workflow = StateGraph(State)
    workflow.add_node("scrape_site", scraper)
    workflow.add_node("validate_context", validate_context)
    workflow.add_node("generate_qa", generate_qa)
    workflow.add_node("validate_qa", validate_qa)
    workflow.add_node("fetch_alternative_link", fetch_alternative_link)

    workflow.add_edge(START, "scrape_site")
    workflow.add_edge("scrape_site", "validate_context")
    workflow.add_conditional_edges("validate_context", context_check_router, {
        "Valid": "generate_qa",
        "Invalid": "fetch_alternative_link",
        "End": END
    })
    workflow.add_edge("fetch_alternative_link", "scrape_site")  # Go back to validation after first retry
    workflow.add_edge("generate_qa", "validate_qa")
    workflow.add_edge("validate_qa", END)
    workflow.add_edge("fetch_alternative_link", END)  # End if retry count is 1

    # Compile graph
    chain = workflow.compile()
    return chain