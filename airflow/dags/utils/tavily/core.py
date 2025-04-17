from tavily import TavilyClient

def web_api(skill, num_results=1, score_threshold=0.50, exclude_domains=[]):
    tavily_client = TavilyClient(os.getenv('TAVILY_API_KEY'))
    response = tavily_client.search(
        query=f"{skill} interview question",
        max_results=num_results,
        exclude_domains=exclude_domains
    )
    return {skill: [res['url'] for res in response['results'] if res['score'] > score_threshold]}