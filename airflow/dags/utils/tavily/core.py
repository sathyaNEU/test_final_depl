from tavily import TavilyClient
import os

def web_api(skill, num_results=1, exclude_domains=[]):
    tavily_client = TavilyClient(os.getenv('TAVILY_API_KEY'))
    response = tavily_client.search(
        query=f"{skill} interview question",
        max_results=num_results,
        exclude_domains=exclude_domains
    )
    if not response['results']:
        return {skill:[]}
    return {skill: [res['url'] for res in response['results']]}