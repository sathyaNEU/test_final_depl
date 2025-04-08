import requests
from bs4 import BeautifulSoup
import json
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
from google.cloud import storage
# from dotenv import load_dotenv
import os 
from datetime import datetime
import uuid
from airflow.hooks.base import BaseHook
from airflow.providers.google.cloud.hooks.gcs import GCSHook
from zoneinfo import ZoneInfo  

# os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "D:/BigDataIntelligence/Assigment/Final_Project/linkedIn_scrapper/gcpkeys.json"

now = datetime.now(ZoneInfo("America/New_York"))
current_year = now.year
current_month = now.month
current_day = now.day
current_hour = now.hour

user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
    ]

proxies = [
    # Format: "http://username:password@proxy_address:port"
    # "http://user:pass@proxy1.example.com:8080",
    # "http://user:pass@proxy2.example.com:8080"
    ]      


def scrape_linkedin_job(url, use_proxy= False):
    """
    Scrape job details from a LinkedIn job posting
    
    """

    
    # Validate URL
    if not url.startswith("http"):
        url = "https://" + url
        
    # Ensure the URL is properly formatted for LinkedIn job posts
    if "linkedin.com" not in url:
        print("Warning: This doesn't appear to be a LinkedIn URL")
        return {"error": "Invalid LinkedIn URL"}
        
    # Setup Chrome options for headless browsing
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    # chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    random_user_agent = random.choice(user_agents)
    # Add a user agent to avoid detection
    chrome_options.add_argument(f"user-agent={random_user_agent}")    

    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    if use_proxy and proxies:
         chrome_options.add_argument(f'--proxy-server={random.choice(proxies)}')

     
    # Initialize the driver with error handling
    try:
        #initialize driver 
        driver = webdriver.Chrome(options=chrome_options)
    except Exception as e:
        print(f"Error initializing Chrome driver: {e}")
        return {"error": "ChromeDriver initialization failed"}
    
    try:
        # Navigate to the job posting
        driver.get(url)
        
        # Wait for the page to load
        time.sleep(random.uniform(3, 5))
        
        # Try to click the "Show more" button to expand the job description if it exists
        try:
            show_more_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".show-more-less-html__button"))
            )
            show_more_button.click()
            time.sleep(1) 
        except:
            pass  # If button is not found or not clickable, just continue
        
        # Get the page source
        page_source = driver.page_source
        
        # Parse the HTML bs4
        soup = BeautifulSoup(page_source, 'html.parser')
        
        job_data = {}
        
        # Job title
        try:
            job_data['title'] = soup.select_one('.top-card-layout__title').text.strip()
        except:
            try:
                job_data['title'] = soup.select_one('h1.topcard__title').text.strip()
            except:
                job_data['title'] = "Not found"
        
        # Company name
        try:
            job_data['company'] = soup.select_one('.topcard__org-name-link').text.strip()
        except:
            try:
                job_data['company'] = soup.select_one('.top-card-layout__card .topcard__flavor-row span:not(.location)').text.strip()
            except:
                try:
                    job_data['company'] = soup.select_one('.topcard__org-name').text.strip()
                except:
                    job_data['company'] = "Not found"
        
        # Location
        try:
            job_data['location'] = soup.select_one('.topcard__flavor--bullet').text.strip()
        except:
            try:
                job_data['location'] = soup.select_one('.top-card-layout__card .topcard__flavor-row .location').text.strip()
            except:
                try:
                    job_data['location'] = soup.select_one('.topcard__subline-location').text.strip()
                except:
                    job_data['location'] = "Not found"
                
        # Posted date
        try:
            job_data['posted_date'] = soup.select_one('.posted-time-ago__text').text.strip()
        except:
            try:
                job_data['posted_date'] = soup.select_one('.top-card-layout__card .topcard__flavor-row span.posted-time-ago__text').text.strip()
            except:
                try:
                    job_data['posted_date'] = soup.select_one('.topcard__flavor--metadata').text.strip()
                except:
                    job_data['posted_date'] = "Not found"
        
        # Job description
        try:
            job_data['description'] = soup.select_one('.description__text').text.strip()
        except:
            try:
                job_data['description'] = soup.select_one('.show-more-less-html__markup').text.strip()
            except:
                try:
                    # Try a more generic approach
                    description_div = soup.select_one('div[class*="description"]')
                    if description_div:
                        job_data['description'] = description_div.text.strip()
                    else:
                        job_data['description'] = "Not found"
                except:
                    job_data['description'] = "Not found"
        
        # Job criteria (seniority, employment type, job function, industries)
        # job_criteria = {}
        criteria_section = soup.select('.description__job-criteria-item')
        
        for criteria in criteria_section:
            try:
                criteria_header = criteria.select_one('.description__job-criteria-subheader').text.strip().replace(" ", "_").lower()
                criteria_value = criteria.select_one('.description__job-criteria-text').text.strip()
                job_data[criteria_header] = criteria_value
            except:
                continue
        
        # job_data['criteria'] = job_criteria
        
    
        # Number of applicants 
        try:
            job_data['applicants'] = soup.select_one('.num-applicants__caption').text.strip()
        except:
            try:
                applicants_element = soup.select_one('span[class*="applicant"]')
                if applicants_element:
                    job_data['applicants'] = applicants_element.text.strip()
                else:
                    job_data['applicants'] = "Not found"
            except:
                job_data['applicants'] = "Not found"
        
        return job_data
    
    except Exception as e:
        print(f"Error: {e}")
        return {"error": str(e)}
    
    finally:
        # Close the browser
        driver.quit()



def scrape_multiple_jobs(job_urls, output_json="linkedin_jobs.json"):
    """
    Scrape multiple job postings and save combined results to JSON
    
    """
    all_jobs = []
    
    for i, url in enumerate(job_urls):
        print(f"Scraping job {i+1}/{len(job_urls)}: {url}")
        job_data = scrape_linkedin_job(url)
        
        if "error" not in job_data:
            all_jobs.append(job_data)
            print(f"Successfully scraped job data for: {job_data.get('title', 'Unknown Title')}")
        else:
            print(f"Failed to scrape job: {job_data.get('error', 'Unknown error')}")
        
        # Add a random delay between requests to avoid detection
        if i < len(job_urls) - 1:
            delay = random.uniform(3, 8)
            print(f"Waiting {delay:.2f} seconds before next request...")
            time.sleep(delay)
    
    # Save combined results to JSON
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(all_jobs, f, indent=4, ensure_ascii=False)
    print(f"All job data saved to {output_json}")



    
def save_to_json(job_data_list, filename="jobs.json"):
    """
    Save multiple job data entries to a JSON file
    """
    # Ensure job_data_list is a list
    if not isinstance(job_data_list, list):
        job_data_list = [job_data_list]
        
    # Check if file already exists to append instead of overwrite
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
            
            # Ensure existing_data is a list
            if not isinstance(existing_data, list):
                existing_data = [existing_data]
                
            # Combine the lists
            combined_data = existing_data + job_data_list
            
    except (FileNotFoundError, json.JSONDecodeError):
        # File doesn't exist or is invalid, use only new data
        combined_data = job_data_list
        
    # Write the combined data
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(combined_data, f, indent=4, ensure_ascii=False)
    
    print(f"Data saved to {filename}")



def get_job_information(**context):
    try:

        # links = kwargs['templates_dict']['links']
        # # Initialize an empty list to store all job data
        all_jobs_data = []
        ti = context['ti']
         
    # Extract role name from task_id
        task_id = context['task'].task_id
        role_name = context['task'].task_id.split('.')[-1] \
            .replace('process_', '') \
            .replace('_jobs', '')

        # Pull data from XCom
        scraped_data = ti.xcom_pull(task_ids='scrape_job_links')        
        links = scraped_data[role_name]

        for i, link in enumerate(links):
            job_uuid = str(uuid.uuid4())
            job_url = link['url']
            job_role = link['role'].replace(" ","_").lower()
            print(f"Scraping job {i+1}/{len(links)}: {job_role} from {job_url}")
            
            # Validate URL before proceeding
            if not job_url or len(job_url) < 10:
                print(f"Error: Invalid URL for {job_role}")
                continue
                
            job_data = scrape_linkedin_job(job_url)
            job_data['role'] = job_role
            job_data['url'] = link['url']


            # Check if there was an error
            if "error" in job_data:
                print(f"Error occurred for {job_role}: {job_data['error']}")
                continue
                
            # Create a temporary file to store the JSON
            temp_file = f"{job_role}.json"
        
        # Write all job data to a single JSON file
              # Write all job data to a single JSON file
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(job_data, f, indent=4, ensure_ascii=False)

            try:
                gcs_hook = GCSHook(gcp_conn_id='google_cloud_default')
                gcs_hook.upload(
                    bucket_name="botfolio",  # Replace with your actual bucket name
                    object_name=f"{current_year}/{current_month}/{current_day}/{current_hour}/{job_role}/{job_role}_{job_uuid}.json",
                    filename=temp_file,
                    mime_type='application/json'
                    )
                print("Data Uploaded successfully")
        
            except Exception as e:
                print("Upload failed")
            
        # Clean up the temporary file
        try:
            os.remove(temp_file)
            print(f"Temporary file {temp_file} removed")
        except Exception as e:
            print(f"Warning: Could not remove temporary file: {e}")

        print(f"All jobs successfully saved to JSON and uploaded to GCS")
        return all_jobs_data
        
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
        return []