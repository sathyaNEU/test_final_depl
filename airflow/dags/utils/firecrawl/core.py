from firecrawl import FirecrawlApp

def scrape_this_site(link):
    app = FirecrawlApp()
    response = app.scrape_url(url=link, params={
        'formats': [ 'markdown' ],
    })
    return response['markdown']