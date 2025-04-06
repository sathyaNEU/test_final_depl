import urllib.parse
import requests
from bs4 import BeautifulSoup
import json
import time
import random
import os
import re



def generate_linkedin_job_url(job_roles, options=None):
    """
    Generates a LinkedIn job search URL for specified job roles
    
    """
    # Base LinkedIn job search URL
    base_url = "https://www.linkedin.com/jobs/search/"
    
    # Default options
    default_options = {
        "time_posted": 1800,  # Last 2 weeks (in hours)
        "location": "",
        "geo_id": "",
        "remote": False
    }
    
    # Use default options if none provided
    if options is None:
        options = {}
    
    # Merge default options with provided options
    search_options = {**default_options, **options}
    
    # Format job roles for URL
    if isinstance(job_roles, list):
        keywords_param = " OR ".join(job_roles)
    else:
        keywords_param = job_roles
    
    params = {}
    
    params["keywords"] = keywords_param
    
    # Add time posted parameter
    if search_options["time_posted"]:
        params["f_TPR"] = f"r{search_options['time_posted']}"
    
    # Add location parameter
    if search_options["location"]:
        params["location"] = search_options["location"]
    
    # Add remote parameter (if enabled)
    if search_options["remote"]:
        params["f_WT"] = "2"
    
    # Build the final URL
    query_string = urllib.parse.urlencode(params)
    return f"{base_url}?{query_string}"



def is_role_relevant(job_title, role_keywords):
    """
    Check if a job title is relevant to the role we're searching for
    """
    job_title = job_title.lower()
    
    # Check if any of the role keywords are in the job title
    for keyword in role_keywords:
        # Use word boundary to ensure we match whole words or parts of compound words
        pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
        if re.search(pattern, job_title):
            return True
            
    return False



def extract_job_title_from_url(url):
    """
    Extract the job title from a LinkedIn job URL

    """
    # Extract the part of the URL that contains the job title (between 'view/' and the job ID)
    match = re.search(r'view/([^/\?]+)', url)
    if match:
        # Convert URL-friendly format to readable text
        job_title = match.group(1)
        # Replace hyphens with spaces and remove job ID if present
        job_title = job_title.replace('-', ' ')
        # Remove any numbers and special characters that might be part of the ID
        job_title = re.sub(r'\d+$', '', job_title).strip()
        return job_title
    return None




def get_role_keywords(role):
    """
    Generate a list of keywords related to a role
    
    """
    # Convert role to lowercase
    role = role.lower()
    
    # common variations and related terms for popular roles
    role_variations = {
        "software engineer": ["software engineer", "software dev", "swe", "software developer", 
                             "programmer", "coder", "software", "backend", "frontend", "fullstack", 
                             "full stack", "back end", "front end", "software development engineer", "sde", "software engineer", "software developer", 
                             "software development"],
                
        "data engineer": ["data engineer", "data pipeline", "etl", "data infrastructure", 
                         "data platform", "data architecture"],
        
        "data scientist": ["data scientist", "machine learning", "ml engineer", "ai scientist", 
                          "analytics", "data analytics", "statistical", "statistics"]
        
    }
    
    # Get variations for the given role, or use the role itself if not found
    keywords = role_variations.get(role, [role])
    
    # Add the original role to ensure it's included
    if role not in keywords:
        keywords.append(role)
    
    # If the role contains spaces, also add a version without spaces
    if " " in role:
        keywords.append(role.replace(" ", ""))
    
    return keywords




def scrape_linkedin_jobs(job_roles, options=None, output_dir='linkedin_scrapper/linkedin_jobs', filter_by_role=True):
    """
    Generates URLs and scrapes job listings for one or multiple job roles,
    filtering results to ensure they're relevant to the searched role
    """
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Convert single role to list for consistent processing
    if not isinstance(job_roles, list):
        job_roles = [job_roles]
    
    # Default headers for requests
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }
    
    results = {}
    
    # Process each job role
    for i, role in enumerate(job_roles):
        # Generate URL for this role
        role_url = generate_linkedin_job_url(role, options)
        
        # Create filename for this role
        safe_role_name = role.replace(" ", "_").lower()
        output_file = os.path.join(output_dir, f"{safe_role_name}.json")
        
        print(f"\nProcessing job role: {role}")
        print(f"URL: {role_url}")
        
        try:
            # Make the request
            response = requests.get(role_url, headers=headers)
            
            # Check if request was successful
            if response.status_code != 200:
                print(f"Error: Received status code {response.status_code}")
                results[role] = []
                continue
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Find all <a> tags and extract links
            links = [a.get("href") for a in soup.find_all("a", href=True)]
            
            # Filter for job links
            filtered_links = []
            for link in links:
                if '/jobs/' in link and '?position=' in link and '&trackingId=' in link:
                    filtered_links.append(link)
            
            # Remove duplicates
            unique_links = list(set(filtered_links))
            
            # Format for JSON and filter by role if enabled
            parsed_links = []
            role_keywords = get_role_keywords(role) if filter_by_role else []
            
            for link in unique_links:
                job_title = extract_job_title_from_url(link)
                
                # If filtering is enabled and we have a job title
                if filter_by_role and job_title:
                    if is_role_relevant(job_title, role_keywords):
                        parsed_links.append({
                            'url': link,
                            'title': job_title,
                            'role': role
                        })
                else:
                    # No filtering or couldn't extract title
                    parsed_links.append({
                        'url': link,
                        'title': job_title,
                        'role': role
                    })
            
            # Save to JSON file
            # with open(output_file, 'w') as f:
            #     json.dump(parsed_links, f, indent=2)
            
            # Store in results
            results[safe_role_name] = parsed_links
            
            print(f"Successfully scraped {len(unique_links)} job links")
            print(f"After filtering: {len(parsed_links)} relevant job links found")
            
            # Add a delay to avoid rate limiting (except after the last request)
            if i < len(job_roles) - 1:
                sleep_time = random.uniform(2, 5)
                print(f"Waiting {sleep_time:.2f} seconds before next request...")
                time.sleep(sleep_time)
                
        except Exception as e:
            print(f"An error occurred while processing {role}: {str(e)}")
            # results[role] = []
    
    # Create a combined file with all results if there are multiple roles
    if len(job_roles) > 1:
        all_links = []
        for role_links in results.values():
            all_links.extend(role_links)
        # Remove duplicates from combined results
        unique_combined = []
        seen_urls = set()
        for item in all_links:
            if item['url'] not in seen_urls:
                seen_urls.add(item['url'])
                unique_combined.append(item)
        
        # combined_file = os.path.join(output_dir, "all_roles_combined.json")
        # with open(combined_file, 'w') as f:
            # json.dump(unique_combined, f, indent=2)
        
        # print(f"\nCombined results: {len(unique_combined)} unique job listings saved to {combined_file}")
    return results


