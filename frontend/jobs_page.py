


import streamlit as st
import pandas as pd
import requests
import datetime
import base64
from dotenv import load_dotenv
import os
import json
from helper import css

load_dotenv()

API_URL = "http://localhost:8000"


def api_request(data=None):
    """Make a request to the consolidated FastAPI endpoint"""
    url = f"{API_URL}/all-jobs-api"
    
    try:
        response = requests.get(url=url)
        response.raise_for_status()
        response_data = response.json  
        return response_data['data'][0]
    
    except requests.RequestException as e:
        st.error(f"API Error: {str(e)}")
        return None
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None

def get_jobs(role=None, time_filter=None, seniority_level=None, employment_type=None):
    """Get job listings from the API with optional filtering"""
    response = requests.get(f'{API_URL}/all-jobs-api/')
    jobs_dict = response.json()["jobs"] if response.status_code==200 else []
    jobs_df = pd.DataFrame(jobs_dict)
    if not jobs_df.empty and "POSTED_DATE" in jobs_df.columns:
        jobs_df["POSTED_DATE"] = pd.to_datetime(jobs_df["POSTED_DATE"])
    return jobs_df
    
    # return pd.DataFrame(columns=["POSTED_DATE", "JOB_ROLE", "TITLE", "COMPANY", "SENIORITY_LEVEL", "EMPLOYMENT_TYPE", "SKILLS", "URL"])

def request_interview_prep(job_role, skills, job_url):
    """Request interview preparation materials"""
    response = api_request({
        "filter": {
            "action": "interview-prep"
        },
        "interview_prep": {
            "job_role": job_role,
            "skills": skills,
            "job_url": job_url
        }
    })
    
    return response

def fetch_cache_status():
    """Fetch cache status from the API"""
    return api_request({
        "filter": {
            "action": "status"
        }
    })

def refresh_cache():
    """Manually refresh the cache"""
    with st.spinner("Refreshing job data..."):
        response = api_request({
            "filter": {
                "action": "refresh"
            }
        })
        if response and response.get("status") == "success":
            st.success("Job data refreshed successfully!")
            return True
        else:
            st.error("Failed to refresh job data.")
            return False

def export_jobs_as_csv(role=None, time_filter=None, seniority_level=None, employment_type=None):
    """Export job listings as CSV"""
    response = api_request({
        "filter": {
            "role": role,
            "time_filter": time_filter,
            "seniority_level": seniority_level,
            "employment_type": employment_type,
            "action": "export"
        }
    })
    
    if response and "csv_data" in response:
        return response["csv_data"]
    
    return None

def format_datetime(dt):
    """Format datetime for display"""
    if pd.isnull(dt):
        return "N/A"
    
    now = datetime.datetime.now()
    delta = now - dt
    
    if delta.days == 0:
        if delta.seconds < 60:
            return "Just now"
        elif delta.seconds < 3600:
            minutes = delta.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            hours = delta.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif delta.days == 1:
        return "Yesterday"
    elif delta.days < 7:
        return f"{delta.days} days ago"
    else:
        return dt.strftime("%b %d, %Y")

def parse_skills(skills_str):
    """Parse skills string into a list"""
    if pd.isna(skills_str) or not skills_str:
        return []
    
    try:
        
        return json.loads(skills_str)
    except:
       
        return [skill.strip() for skill in skills_str.split(",") if skill.strip()]

# Initialize session state
if 'first_load' not in st.session_state:
    st.session_state.first_load = True
    st.session_state.jobs_data = None
    st.session_state.selected_role = "All Roles"
    st.session_state.selected_time = "All Time"
    st.session_state.selected_seniority = "All Levels"
    st.session_state.selected_employment = "All Types"
    st.session_state.filters_applied = False
    st.session_state.filter_pending = False
    st.session_state.interview_prep_job = None

def main():

    if not hasattr(st, 'already_set_page_config'):
            st.set_page_config(
                page_title="Latest Job Listings", 
                page_icon="🔍", 
                layout="wide", 
                initial_sidebar_state="expanded"
            )
            # Mark that we've set the config
            st._is_running_with_streamlit = True
            st.already_set_page_config = True
        
        # Rest of your jobs page code
    st.markdown("<h1 class='app-header'>🔍 Latest Job Listings</h1>", unsafe_allow_html=True)
    st.markdown("<p class='app-subtitle'>Find the latest job openings matching your skills and preferences</p>", unsafe_allow_html=True)
        
    #Add custom CSS for better styling
    st.markdown(css, unsafe_allow_html=True)

    st.sidebar.title("Job Data Cache")
    cache_status = fetch_cache_status()
    
    if cache_status:
        last_refresh = "Never"
        if cache_status.get("last_refresh"):
            try:
                last_refresh_time = datetime.datetime.fromisoformat(cache_status["last_refresh"])
                last_refresh = format_datetime(last_refresh_time)
            except:
                last_refresh = cache_status["last_refresh"]
        
        if "cache_exists" in cache_status and cache_status["cache_exists"]:
            job_count = cache_status.get("job_count", 0)
            st.sidebar.success(f"✅ Cache Status: Active\n\nLast Refresh: {last_refresh}\n\nCached Jobs: {job_count}")
        else:
            st.sidebar.warning("⚠️ Cache not initialized")
            
        # Manual refresh button
        if st.sidebar.button("🔄 Refresh Job Data", key="refresh_cache"):
            if refresh_cache():
                st.session_state.jobs_data = None
                st.session_state.first_load = True
                st.session_state.filters_applied = False
                st.experimental_rerun()
    
   
    st.sidebar.title("Filter Options")
    
    
    role_options = ["All Roles", "data_engineer", "data_scientist", "software_engineer"]
    selected_role = st.sidebar.selectbox(
        "Job Role",
        role_options,
        index=role_options.index(st.session_state.selected_role) if st.session_state.selected_role in role_options else 0,
    )
    
    
    seniority_options = [
        "All Levels", "Entry level", "Associate", "Internship", 
        "Mid-Senior level", "Director", "Not Applicable"
    ]
    selected_seniority = st.sidebar.selectbox(
        "Seniority Level",
        seniority_options,
        index=seniority_options.index(st.session_state.selected_seniority) if st.session_state.selected_seniority in seniority_options else 0,
    )
    
    
    employment_options = ["All Types", "Full-time", "Part-time", "Contract"]
    selected_employment = st.sidebar.selectbox(
        "Employment Type",
        employment_options,
        index=employment_options.index(st.session_state.selected_employment) if st.session_state.selected_employment in employment_options else 0,
    )
    
    
    time_options = [
        "All Time",
        "Last 30 minutes", 
        "Last hour", 
        "Last 2 hours", 
        "Last 3 hours",
        "Last 4 hours"
    ]
    selected_time = st.sidebar.selectbox(
        "Posted Within",
        time_options,
        index=time_options.index(st.session_state.selected_time) if st.session_state.selected_time in time_options else 0,
    )
    
    
    filters_changed = (
        selected_role != st.session_state.selected_role or
        selected_time != st.session_state.selected_time or
        selected_seniority != st.session_state.selected_seniority or
        selected_employment != st.session_state.selected_employment
    )
    
    if filters_changed:
        st.session_state.filter_pending = True
    
    
    if st.sidebar.button("Apply Filters", key="apply_filters") or st.session_state.filters_applied == False:
        st.session_state.selected_role = selected_role
        st.session_state.selected_time = selected_time
        st.session_state.selected_seniority = selected_seniority
        st.session_state.selected_employment = selected_employment
        st.session_state.filters_applied = True
        st.session_state.filter_pending = False
    
    
    if st.sidebar.button("Reset Filters", key="reset_filters"):
        st.session_state.selected_role = "All Roles"
        st.session_state.selected_time = "All Time"
        st.session_state.selected_seniority = "All Levels"
        st.session_state.selected_employment = "All Types"
        st.session_state.filters_applied = True
        st.session_state.filter_pending = False
        st.experimental_rerun()
    
   
    export_button = st.sidebar.button("📊 Export Filtered Data", key="export_csv")
    
   
    if st.session_state.filter_pending:
        st.sidebar.warning("⚠️ Filter changes not applied yet. Click 'Apply Filters' to update results.")
    
    
    api_role = None if st.session_state.selected_role == "All Roles" else st.session_state.selected_role
    api_seniority = None if st.session_state.selected_seniority == "All Levels" else st.session_state.selected_seniority
    api_employment = None if st.session_state.selected_employment == "All Types" else st.session_state.selected_employment
    
    api_time = None
    if st.session_state.selected_time == "Last 30 minutes":
        api_time = "30min"
    elif st.session_state.selected_time == "Last hour":
        api_time = "1hr"
    elif st.session_state.selected_time == "Last 2 hours":
        api_time = "2hr" 
    elif st.session_state.selected_time == "Last 3 hours":
        api_time = "3hr"
    elif st.session_state.selected_time == "Last 4 hours":
        api_time = "4hr"
    
    
    if st.session_state.first_load or st.session_state.jobs_data is None:
        with st.spinner("Loading job listings..."):
            all_jobs_df = get_jobs()
            if all_jobs_df is not None and not all_jobs_df.empty:
                st.session_state.jobs_data = all_jobs_df
                st.session_state.first_load = False
                st.write(all_jobs_df)
            else:
                st.warning("Failed to load job listings. Please try refreshing the page.")
    
    
    jobs_df = None
    if st.session_state.jobs_data is not None:
        jobs_df = st.session_state.jobs_data.copy()
        
        
        if api_role:
            jobs_df = jobs_df[jobs_df["JOB_ROLE"] == api_role]
        
        
        if api_seniority:
            
            if "SENIORITY_LEVEL" in jobs_df.columns:
                jobs_df = jobs_df[jobs_df["SENIORITY_LEVEL"].fillna("Not Applicable") == api_seniority]
        
        
        if api_employment:
            
            if "EMPLOYMENT_TYPE" in jobs_df.columns:
                jobs_df = jobs_df[jobs_df["EMPLOYMENT_TYPE"].fillna("Not Applicable") == api_employment]
        
        
        if api_time:
            hours_map = {
                "30min": 0.5,
                "1hr": 1,
                "2hr": 2,
                "3hr": 3,
                "4hr": 4
            }
            hours = hours_map.get(api_time, 0)
            if hours > 0:
                cutoff_time = datetime.datetime.now() - datetime.timedelta(hours=hours)
                jobs_df = jobs_df[jobs_df["POSTED_DATE"] >= cutoff_time]
        
       
        if export_button and jobs_df is not None:
            csv_data = export_jobs_as_csv(
                role=api_role,
                time_filter=api_time,
                seniority_level=api_seniority,
                employment_type=api_employment
            )
            if csv_data:
                st.sidebar.download_button(
                    label="⬇️ Download CSV File",
                    data=csv_data,
                    file_name=f"job_listings_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv"
                )
                st.sidebar.success("CSV file ready for download!")
            else:
                st.sidebar.error("Failed to generate CSV file. Please try again.")
                
        # Show applied filters as tags
        filter_tags = []
        if api_role:
            filter_tags.append(f"Role: {api_role}")
        if api_seniority:
            filter_tags.append(f"Level: {api_seniority}")
        if api_employment:
            filter_tags.append(f"Type: {api_employment}")
        if api_time:
            filter_tags.append(f"Time: {st.session_state.selected_time}")
            
        if filter_tags:
            filter_html = "<div class='filter-tags'><strong>Active Filters:</strong> " + " ".join([f"<span class='filter-tag'>{tag}</span>" for tag in filter_tags]) + "</div>"
            st.markdown(filter_html, unsafe_allow_html=True)
        
        # Show job count
        if jobs_df.empty:
            st.warning("No job listings found matching your criteria.")
        else:
            st.write(f"Found **{len(jobs_df)}** job listings")
            
           
            for idx, job in jobs_df.iterrows():
                
                job_title = job.get('TITLE') if pd.notna(job.get('TITLE')) else job.get('JOB_ROLE', 'Unknown Position')
                job_company = job.get('COMPANY') if pd.notna(job.get('COMPANY')) else 'Unknown Company'
                job_role = job.get('JOB_ROLE', '')
                job_url = job.get('URL', '#')
                job_seniority = job.get('SENIORITY_LEVEL') if pd.notna(job.get('SENIORITY_LEVEL')) else 'Not Specified'
                job_employment = job.get('EMPLOYMENT_TYPE') if pd.notna(job.get('EMPLOYMENT_TYPE')) else 'Not Specified'
                posted_date = format_datetime(job.get('POSTED_DATE')) if pd.notna(job.get('POSTED_DATE')) else 'Unknown'
                
                
                skills_str = job.get('SKILLS')
                skills = parse_skills(skills_str)
                skills_html = ""
                if skills:
                    skills_html = "".join([f"<span class='skill-tag'>{skill}</span>" for skill in skills])
                else:
                    skills_html = "<em>No skills listed</em>"
                
                
                job_key = f"job-{idx}"



                with st.container():
                    job_card = f"""
                    <div class="job-card">
                        <div class="job-title">{job_title}</div>
                        <div class="job-company">{job_company}</div>
                        <div class="job-meta">
                            <span class="job-role-tag">{job_role}</span>
                            <span style="margin-left: 10px;">{job_seniority}</span>
                            <span style="margin-left: 10px;">{job_employment}</span>
                        </div>
                        <div class="job-date">Posted: {posted_date}</div>
                        <div class="job-buttons">
                            <a href="{job_url}" target="_blank" class="view-button">View Job Listing</a>
                            <a href="#" onclick="event.preventDefault(); document.getElementById('prep-{job_key}').click();" class="prep-button">Prepare for Interview</a>
                        </div>
                    """

                    # Add skills if any
                    if skills:
                        job_card += "<div class='skills-title'>🔧 Skills</div>"
                        skills_html = "".join([f"<span class='skill-tag'>{skill}</span>" for skill in skills])
                        job_card += skills_html
                    else:
                        job_card += "<div class='skills-title'>🔧 Skills</div><em>No skills listed</em>"

                    job_card += "</div>"

                    st.markdown(job_card, unsafe_allow_html=True)
                    st.markdown("<hr style='margin: 30px 0; border: none; border-top: 1px solid #eee;'>", unsafe_allow_html=True)
                
               
if __name__ == "__main__":
    main()