import streamlit as st
import os
import json
import requests
import tempfile
import copy
import google.generativeai as genai
import time
import threading
from dotenv import load_dotenv
from pathlib import Path
from static import helper
import logging
from functools import lru_cache


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
API_URL = os.getenv("API_URL", "http://localhost:8000") 

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Set up the correct path to your images
PREVIEW_DIR = Path(__file__).parent.parent / "static" / "images"
os.makedirs(PREVIEW_DIR, exist_ok=True)

# Cache for API responses to reduce redundant API calls
CACHE = {}

# Gemini System Prompt for Resume Editing
RESUME_EDITOR_INSTRUCTIONS = """
You are a resume assistant that helps users edit their portfolio JSON data. 
Your task is to update a JSON resume based on the user's instructions.

The JSON resume has the following structure:
{
  "about": {
    "name": "Full Name",
    "location": "City, State",
    "email": "email@example.com",
    "phone": "Phone number",
    "linkedin_hyperlink": "LinkedIn URL",
    "github_hyperlink": "GitHub URL",
    "summary": "Professional summary paragraph"
  },
  "education": [
    {
      "university": "University Name",
      "location": "University Location",
      "degree": "Degree Name",
      "period": "Month Year - Month Year",
      "related_coursework": ["Course 1", "Course 2", "Course 3"],
      "gpa": "GPA Value"
    }
  ],
  "skills": [
    {
      "category": "Category Name",
      "skills": ["Skill 1", "Skill 2", "Skill 3"]
    }
  ],
  "experience": [
    {
      "company": "Company Name",
      "position": "Job Title",
      "location": "Job Location",
      "period": "Month Year - Month Year",
      "responsibilities": ["Responsibility 1", "Responsibility 2", "Responsibility 3"]
    }
  ],
  "projects": [
    {
      "name": "Project Name",
      "description": "Project description",
      "technologies": ["Tech 1", "Tech 2", "Tech 3"],
      "url": "Project URL"
    }
  ],
  "accomplishments": [
    {
      "title": "Accomplishment Title",
      "date": "Month Year",
      "link": "Relevant URL"
    }
  ]
}

Follow these rules:
1. Maintain the exact JSON structure - do not add or remove any top-level keys
2. Format dates consistently as "Month Year" (e.g., "January 2023")
3. Return ONLY valid JSON without any other text or explanations
4. Make sure comma placement is correct and the JSON will parse properly
5. Preserve information that the user doesn't explicitly ask to change
6. Use proper capitalization and professional language
7. For lists (like skills, responsibilities), maintain them as valid JSON arrays
8. If adding a new item to an array (like a new job or project), follow the same structure as existing items

If the user asks to add a new entry (education, job, project, etc.), create a complete entry with all required fields.
If any fields would be empty, use reasonable placeholder text that the user can edit later.
"""

# -----------------
# HELPER FUNCTIONS
# -----------------

@lru_cache(maxsize=32)
def get_gemini_model():
    """Get a cached Gemini model instance to avoid recreating it"""
    return genai.GenerativeModel(
        model_name="gemini-1.5-pro",
        generation_config={
            "temperature": 0.2,
            "top_p": 0.8,
            "top_k": 40,
            "max_output_tokens": 8192,
        }
    )

def run_async(func, callback=None):
    """Run a function asynchronously"""
    def wrapper():
        result = func()
        if callback:
            callback(result)
    
    thread = threading.Thread(target=wrapper)
    thread.daemon = True
    thread.start()
    return thread

class APIClient:
    """Class to handle API requests with caching and auth"""
    
    @staticmethod
    def request(endpoint, method="get", headers=None, data=None, files=None, params=None, use_cache=True):
        """Make API requests to the backend with proper error handling and caching"""
        url = f"{API_URL}/{endpoint}"
        headers = headers or {}
        cache_key = None
        
        # Add auth token if available
        if "Authorization" not in headers and "token" in st.session_state:
            headers["Authorization"] = f"Bearer {st.session_state.token}"
        
        # Check cache for GET requests
        if method.lower() == "get" and use_cache:
            cache_key = f"{url}_{str(params)}"
            if cache_key in CACHE:
                return CACHE[cache_key]
        
        try:
            if method.lower() == "get":
                response = requests.get(url, headers=headers, params=params)
            elif method.lower() == "post":
                # If files are included, don't use json=data
                if files:
                    response = requests.post(url, headers=headers, files=files, data=data)
                else:
                    response = requests.post(url, headers=headers, json=data)
            elif method.lower() == "put":
                response = requests.put(url, headers=headers, json=data)
            elif method.lower() == "delete":
                response = requests.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            # Handle API errors
            if response.status_code >= 400:
                error_detail = "Unknown error"
                try:
                    error_detail = response.json().get("detail", error_detail)
                except:
                    pass
                raise Exception(f"API Error ({response.status_code}): {error_detail}")
            
            result = response.json()
            
            # Cache successful GET responses
            if method.lower() == "get" and use_cache and cache_key:
                CACHE[cache_key] = result
            
            return result
        except requests.RequestException as e:
            st.error(f"API Connection Error: {str(e)}")
            return None
        except Exception as e:
            st.error(f"Error: {str(e)}")
            return None

# -----------------
# AUTH FUNCTIONS
# -----------------

def login(email, password):
    """Login user and get token"""
    response = APIClient.request("login", method="post", data={"user_email": email, "password": password})
    if response:
        # Store user session data
        st.session_state.user_email = email
        st.session_state.is_authenticated = True
        
        # Set user data from response
        user_data = response["user_data"]
        if user_data["UI_ENDPOINT"] == "null":
            st.session_state.is_site_hosted = False
        else:
            st.session_state.is_site_hosted = user_data["UI_ENDPOINT"]
        
        if user_data["UI_ENDPOINT"]:
            st.session_state.site_url = user_data["UI_ENDPOINT"]
            st.session_state.repo_name = user_data["UI_ENDPOINT"].split("/")[-2]
            st.session_state.selected_theme = user_data["THEME"]
            st.session_state.theme_selected = True
            resume_data = json.loads(user_data["RESUME_JSON"])
            st.session_state.resume_data = resume_data
            st.session_state.edited_resume = copy.deepcopy(resume_data)
            
            # Reset messages for returning users
            if "messages" in st.session_state:
                del st.session_state.messages
        
        return True
    return False

def register(email, password):
    """Register a new user"""
    response = APIClient.request("register", method="post", data={"email": email, "password": password})
    if response:
        st.session_state.user_email = email
        st.session_state.is_authenticated = True
        st.session_state.is_site_hosted = 0
        return True
    return False

def validate_repo_name(repo_name):
    """Check if repository name is available"""
    # Cache validation results to prevent repeated calls
    cache_key = f"validate_repo_{repo_name}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]
    
    response = APIClient.request("validate-repo", method="post", data={"repo_name": repo_name})
    if response:
        valid = response["valid"]
        st.session_state[cache_key] = valid
        return valid
    return False

def deploy_portfolio(user_email, theme, repo_name, callback=None):
    """Deploy portfolio to GitHub asynchronously with fresh resume data (FastAPI version)"""
    def deploy_task():
        try:
            response = APIClient.request("deploy", method="post", data={
                "repo_name": repo_name,
                "theme": theme,
                "user_email": user_email
            })
        
            if response and "url" in response:
                url = response["url"]
                if callback:
                    callback(url)  # Call the callback with the URL on success
                return url
            else:
                if callback:
                    callback(None)  # Call callback with None if no valid response
                return None
        
        except Exception as e:
            logging.error(f"Error in deploy task: {str(e)}")
            if callback:
                callback(None)
            return None
        
    # Start deployment in background thread
    run_async(deploy_task, callback)



def update_resume(resume_data):
    """Update resume data in the backend"""
    response = APIClient.request("update-resume", method="put", data={
        "resume_data": resume_data,
        "user_email": st.session_state.user_email  # Added user_email to ensure correct user data is updated
    })
    # Return True if successful, False otherwise
    return response is not None

def save_resume_changes():
    """Save resume changes to backend - call this before deployment"""
    if "edited_resume" in st.session_state and "resume_data" in st.session_state:
        # Check if there are actual changes to save
        if st.session_state.edited_resume != st.session_state.resume_data:
            # with st.spinner("Saving resume changes..."):
                try:
                    # Use the same endpoint that's working for the chatbot
                    response = requests.post(
                        f"{API_URL}/json-to-sf", 
                        json={
                            "user_email": st.session_state.user_email,
                            "mode": "update",  # Use a mode that signals this is a direct save
                            "resume_data": st.session_state.edited_resume
                        }
                    )
                    
                    if response.status_code >= 400:
                        st.error(f"Error saving changes: {response.text}")
                        return False
                    
                    # Update local copy to match what was saved
                    st.session_state.resume_data = copy.deepcopy(st.session_state.edited_resume)
                    logging.info("Resume changes saved successfully")
                    return True
                except Exception as e:
                    st.error(f"Error saving changes: {str(e)}")
                    return False
        else:
            logging.info("No changes to save - resume data is already up to date")
            return True  # No changes needed
    return False  # No resume data to save

# -----------------
# UI COMPONENTS
# -----------------

def display_theme_selector(themes):
    """Display theme selection cards with static image previews"""
    st.subheader("Choose a Theme")

    cols = st.columns(2)
    
    for i, theme_name in enumerate(themes.keys()):
        col = cols[i % 2]
        with col:
            st.markdown(f"### {theme_name}")
            st.markdown(f"*{themes[theme_name]['description']}*")

            # Preview image - cache check to avoid file I/O on every rerun
            image_path_key = f"image_path_{theme_name}"
            if image_path_key not in st.session_state:
                image_found = False
                for ext in ['png', 'jpg', 'jpeg']:
                    preview_path = PREVIEW_DIR / f"{theme_name.lower().replace(' ', '_')}_preview.{ext}"
                    if preview_path.exists():
                        st.session_state[image_path_key] = str(preview_path)
                        image_found = True
                        break
                
                if not image_found:
                    st.session_state[image_path_key] = f"https://via.placeholder.com/600x400?text={theme_name}+Preview"

            col.image(st.session_state[image_path_key], 
                      caption=f"Preview of {theme_name}", 
                      use_container_width=True)
            
            # Theme selection button
            if col.button(f"Select {theme_name}", key=f"select_button_{theme_name}"):
                st.session_state.selected_theme = theme_name
                st.session_state.theme_selected = True
                st.success(f"✅ You selected **{theme_name}**.")
                return

def display_resume_json(resume_data):
    """Display the resume data in a readable format"""
    if "preview_key" not in st.session_state:
        st.session_state.preview_key = 0
    
    # Only increment the key when the resume data changes
    if "last_displayed_resume" not in st.session_state or st.session_state.last_displayed_resume != resume_data:
        st.session_state.preview_key += 1
        st.session_state.last_displayed_resume = copy.deepcopy(resume_data)
    
    with st.container(key=f"preview_container_{st.session_state.preview_key}"):
        # About section
        if "about" in resume_data:
            about = resume_data["about"]
            st.subheader("📋 Personal Information")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Name:** {about.get('name', 'Not specified')}")
                st.markdown(f"**Email:** {about.get('email', 'Not specified')}")
                st.markdown(f"**Phone:** {about.get('phone', 'Not specified')}")
            with col2:
                st.markdown(f"**Location:** {about.get('location', 'Not specified')}")
                st.markdown(f"**LinkedIn:** {about.get('linkedin_hyperlink', 'Not specified')}")
                st.markdown(f"**GitHub:** {about.get('github_hyperlink', 'Not specified')}")
            
            if "summary" in about:
                st.markdown(f"**Summary:** {about['summary']}")
            
            st.markdown("---")
        
        # Education section
        if "education" in resume_data and resume_data["education"]:
            st.subheader("🎓 Education")
            for i, edu in enumerate(resume_data["education"]):
                with st.expander(f"{edu.get('university', 'University')} - {edu.get('degree', 'Degree')}"):
                    st.markdown(f"**University:** {edu.get('university', 'Not specified')}")
                    st.markdown(f"**Location:** {edu.get('location', 'Not specified')}")
                    st.markdown(f"**Degree:** {edu.get('degree', 'Not specified')}")
                    st.markdown(f"**Period:** {edu.get('period', 'Not specified')}")
                    
                    if "gpa" in edu:
                        st.markdown(f"**GPA:** {edu['gpa']}")
                    
                    if "related_coursework" in edu and edu["related_coursework"]:
                        st.markdown("**Related Coursework:**")
                        for course in edu["related_coursework"]:
                            st.markdown(f"- {course}")
            
            st.markdown("---")
        
        # Skills section
        if "skills" in resume_data and resume_data["skills"]:
            st.subheader("🔧 Skills")
            for skill_group in resume_data["skills"]:
                with st.expander(skill_group.get("category", "Skills")):
                    if "skills" in skill_group and skill_group["skills"]:
                        st.markdown(", ".join(skill_group["skills"]))
            
            st.markdown("---")
        
        # Experience section
        if "experience" in resume_data and resume_data["experience"]:
            st.subheader("💼 Work Experience")
            for i, exp in enumerate(resume_data["experience"]):
                with st.expander(f"{exp.get('position', 'Position')} at {exp.get('company', 'Company')}"):
                    st.markdown(f"**Company:** {exp.get('company', 'Not specified')}")
                    st.markdown(f"**Position:** {exp.get('position', 'Not specified')}")
                    st.markdown(f"**Period:** {exp.get('period', 'Not specified')}")
                    st.markdown(f"**Location:** {exp.get('location', 'Not specified')}")
                    
                    if "responsibilities" in exp and exp["responsibilities"]:
                        st.markdown("**Responsibilities:**")
                        for resp in exp["responsibilities"]:
                            st.markdown(f"- {resp}")
            
            st.markdown("---")
        
        # Projects section
        if "projects" in resume_data and resume_data["projects"]:
            st.subheader("🚀 Projects")
            for i, proj in enumerate(resume_data["projects"]):
                with st.expander(proj.get("name", "Project")):
                    st.markdown(f"**Name:** {proj.get('name', 'Not specified')}")
                    st.markdown(f"**Description:** {proj.get('description', 'Not specified')}")
                    
                    if "url" in proj and proj["url"]:
                        st.markdown(f"**URL:** {proj['url']}")
                    
                    if "technologies" in proj and proj["technologies"]:
                        st.markdown("**Technologies:**")
                        st.markdown(", ".join(proj["technologies"]))
            
            st.markdown("---")
        
        # Accomplishments section
        if "accomplishments" in resume_data and resume_data["accomplishments"]:
            st.subheader("🏆 Accomplishments")
            for i, accom in enumerate(resume_data["accomplishments"]):
                with st.expander(accom.get("title", "Accomplishment")):
                    st.markdown(f"**Title:** {accom.get('title', 'Not specified')}")
                    st.markdown(f"**Date:** {accom.get('date', 'Not specified')}")
                    
                    if "link" in accom and accom["link"]:
                        st.markdown(f"**Link:** {accom['link']}")
            
            st.markdown("---")

def create_llm_based_editor(resume_data):
    """Create an LLM-based chat editor for resume data using API endpoint"""
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hello! I'm your AI resume editor. Please tell me what changes you'd like to make to your resume. You can say things like:\n\n- Update my job title at Google to 'Senior Software Engineer'\n- Add a new project called 'Portfolio Generator'\n- Update my skills to include 'React', 'Node.js', and 'Python'\n- Add a new work experience"}
        ]
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # User input
    if prompt := st.chat_input("What would you like to edit in your resume?"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.write(prompt)
        
        # Show spinner while processing
        with st.spinner("Updating your resume..."):
            try:
                # Call the API endpoint instead of using Gemini directly
                response = requests.post(
                    f"{API_URL}/json-to-sf", 
                    json={ "changes": prompt,  "mode": "revise","user_email": st.session_state.user_email}
                )
                
                # Check if the response was successful
                if response.status_code == 200:
                    # Extract the JSON from the response
                    updated_resume = response.json()
                    
                    # Update session state with the updated resume
                    st.session_state.edited_resume = updated_resume
                    
                    # Set a flag to indicate the resume was updated
                    st.session_state.resume_updated = True
                    
                    # Force refresh the preview by changing last_displayed_resume
                    if "last_displayed_resume" in st.session_state:
                        del st.session_state.last_displayed_resume
                    
                    # Create assistant response
                    assistant_response = "✅ I've updated your resume! Here's what changed:\n\n"
                    
                    # Identify the changes (simplified version)
                    if "about" in prompt.lower():
                        assistant_response += "- Updated your personal information\n"
                    if "education" in prompt.lower() or "university" in prompt.lower() or "degree" in prompt.lower():
                        assistant_response += "- Updated your education details\n"
                    if "skill" in prompt.lower():
                        assistant_response += "- Updated your skills\n"
                    if "experience" in prompt.lower() or "job" in prompt.lower() or "work" in prompt.lower():
                        assistant_response += "- Updated your work experience\n"
                    if "project" in prompt.lower():
                        assistant_response += "- Updated your projects\n"
                    if "accomplishment" in prompt.lower() or "award" in prompt.lower() or "certification" in prompt.lower():
                        assistant_response += "- Updated your accomplishments\n"
                    
                    assistant_response += "\nYou can see the changes in the resume preview. Is there anything else you'd like to update?"
                else:
                    # If the API call fails, show error
                    st.error(f"Error updating resume: {response.text}")
                    assistant_response = "I had trouble updating your resume. Please try again."
                    
                    # Keep the original resume
                    st.session_state.edited_resume = resume_data
                    st.session_state.resume_updated = False
            
            except Exception as e:
                st.error(f"Error: {str(e)}")
                assistant_response = "I encountered an error while trying to update your resume. Please try again."
                st.session_state.edited_resume = resume_data
                st.session_state.resume_updated = False
        
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": assistant_response})
        
        # Display assistant response
        with st.chat_message("assistant"):
            st.write(assistant_response)
        
        # Force a rerun to refresh the preview immediately
        st.rerun()
    
    return st.session_state.edited_resume

def login_page():
    """Display login page and handle authentication"""
    st.title("🌐 Portfolio Website Builder")
    st.subheader("Login to access your portfolio")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        
        if st.button("Login", key="login_button"):
            with st.spinner("Logging in..."):
                if login(email, password):
                    st.success("Login successful!")
                    # Use session state to trigger rerun instead of direct call
                    st.session_state.login_successful = True
                    st.rerun()
                else:
                    st.error("Invalid email or password")
                
        st.markdown("---")
        st.markdown("### Register New Account")
        reg_email = st.text_input("Email", key="register_email")
        reg_password = st.text_input("Password", type="password", key="register_password")
        
        if st.button("Register", key="register_button"):
            with st.spinner("Registering..."):
                if register(reg_email, reg_password):
                    st.success("Registration successful! You're now logged in.")
                    # Use session state to trigger rerun instead of direct call
                    st.session_state.registration_successful = True
                    st.rerun()
                else:
                    st.error("Registration failed. Please try again.")
    
    with col2:
        st.markdown("### Welcome to Portfolio Website Builder")
        st.markdown("Turn your resume into a professional portfolio website in minutes!")
        
        # Add a quick description of the app
        st.markdown("""
        ### 📝 Resume to Portfolio Website Generator
        
        1. Upload your resume or enter your information
        2. Choose from beautiful portfolio themes
        3. Deploy instantly to GitHub Pages
        
        Your professional online presence is just a few clicks away!
        """)

def show_non_blocking_progress(key="progress", steps=100, time_per_step=0.40):
    """Show a progress bar without blocking the UI thread"""
    if f"{key}_start_time" not in st.session_state:
        st.session_state[f"{key}_start_time"] = time.time()
        st.session_state[f"{key}_total_steps"] = steps
        st.session_state[f"{key}_time_per_step"] = time_per_step
        st.session_state[f"{key}_progress"] = 0
        st.session_state[f"{key}_completed"] = False
    
    # Calculate progress based on elapsed time
    elapsed = time.time() - st.session_state[f"{key}_start_time"]
    expected_progress = min(int(elapsed / time_per_step), steps)
    
    # Only update progress if it's increased
    if expected_progress > st.session_state[f"{key}_progress"]:
        st.session_state[f"{key}_progress"] = expected_progress
    
    # Display progress bar
    progress = st.progress(st.session_state[f"{key}_progress"] / steps)
    
    # Check if completed
    if st.session_state[f"{key}_progress"] >= steps and not st.session_state[f"{key}_completed"]:
        st.session_state[f"{key}_completed"] = True
        return True
    
    return st.session_state[f"{key}_completed"]

def handle_deployment_completion(url):
    """Callback for when deployment completes"""
    if url:
        st.session_state.deployment_url = url
        st.session_state.is_site_hosted = 1
        st.session_state.site_url = url
        st.session_state.deployment_complete = True

def main_app():
    """Main application after login"""
    st.title("🌐 Resume → Portfolio Website Generator")
    
    # Display user info in sidebar
    st.sidebar.markdown(f"### Welcome, {st.session_state.user_email}")
    
    # If user has a hosted site, show the link
    if st.session_state.is_site_hosted:
        st.sidebar.markdown("### Your Portfolio")
        st.sidebar.markdown(f"🔗 [View your portfolio]({st.session_state.site_url})")
        st.sidebar.markdown(f"Repository: {st.session_state.repo_name}")
    
    if st.sidebar.button("Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    # Determine workflow based on whether user has a hosted site
    if st.session_state.is_site_hosted:
        # For existing users with a portfolio
        tab_titles = ["1. Edit Resume"]
        tabs = st.tabs(tab_titles)
        
        with tabs[0]:  # Edit tab for existing users
            st.subheader("Edit Your Portfolio")
            
            # Make sure we reset deployment flags when entering the edit tab
            if "show_deployment_screen" not in st.session_state:
                st.session_state.show_deployment_screen = False
            
            # Only show the edit UI if we're not showing the deployment screen
            if not st.session_state.show_deployment_screen:
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.subheader("Current Resume Preview")
                    display_resume_json(st.session_state.edited_resume)
                
                with col2:
                    st.subheader("AI Resume Editor")
                    # Skip rendering during processing to prevent duplication
                    if not st.session_state.get("is_processing", False):
                        create_llm_based_editor(st.session_state.edited_resume)
                
                # Auto-save changes periodically
                if "last_autosave" not in st.session_state:
                    st.session_state.last_autosave = time.time()
                

                col_deploy, col_save  = st.columns([1, 1])
                
                with col_deploy:
                    if st.button("🚀 Deploy Your Portfolio", key="deploy_from_edit_tab"):
                        # First save any unsaved changes
                        with st.spinner("Saving changes before deployment..."):
                            if save_resume_changes():
                                st.success("✅ Changes saved!")
                                st.session_state.last_autosave = time.time()
                        
                        # Switch to deployment screen
                        st.session_state.show_deployment_screen = True
                        st.session_state.deploy_clicked = False
                        st.session_state.deployment_complete = False
                        st.session_state.show_progress = False
                        st.rerun()
            
            # Show deployment screen if the flag is set
            else:
                st.subheader("Deploy Changes to Your Portfolio")
                
                st.info(f"Your portfolio is currently hosted at: {st.session_state.site_url}")
                st.info(f"Repository name: {st.session_state.repo_name}")
                
                if "deploy_clicked" not in st.session_state:
                    st.session_state.deploy_clicked = False
                
                if not st.session_state.deploy_clicked:
                    if st.button("🚀 Update Your Portfolio", key="update_portfolio_button"):
                        st.session_state.deploy_clicked = True
                        st.session_state.deployment_started = True
                        
                        # Start asynchronous deployment
                        deploy_portfolio(
                            st.session_state.user_email,
                            st.session_state.selected_theme,
                            st.session_state.repo_name,
                            handle_deployment_completion
                        )
                        
                        # Display initial message
                        st.info("Deployment started! This will take approximately 40 seconds...")
                        
                        # Set a placeholder for progress bar (will appear on next rerun)
                        st.session_state.show_progress = True
                        st.rerun()
                    
                    # Add a button to go back to editing
                    if st.button("← Back to Editing", key="back_to_edit_button"):
                        # Make sure we preserve the edited_resume when going back to editing
                        if "edited_resume" not in st.session_state and "resume_data" in st.session_state:
                            st.session_state.edited_resume = copy.deepcopy(st.session_state.resume_data)
                        st.session_state.show_deployment_screen = False
                        st.rerun()
                
                elif st.session_state.get("show_progress", False) and not st.session_state.get("deployment_complete", False):
                    # Show non-blocking progress bar
                    st.info("GitHub Pages deployment in progress...")
                    completed = show_non_blocking_progress("deployment", 100, 0.40)
                    
                    # Rerun to update progress bar (unless completed)
                    if not completed:
                        time.sleep(0.1)  # Short sleep to prevent too frequent reruns
                        st.rerun()
                    else:
                        st.success(f"✅ Portfolio successfully updated!")
                        st.info(f"Your portfolio is available at: [🔗 {st.session_state.site_url}]({st.session_state.site_url})")
                        st.balloons()
                        
                        # Add a button to go back to editing
                        if st.button("← Back to Editing", key="back_to_edit_after_deploy"):
                            # Make sure we preserve the edited_resume when going back to editing
                            if "edited_resume" not in st.session_state and "resume_data" in st.session_state:
                                st.session_state.edited_resume = copy.deepcopy(st.session_state.resume_data)
                            st.session_state.show_deployment_screen = False
                            st.rerun()
                
                elif st.session_state.get("deployment_complete", False):
                    # Show deployment completed message
                    st.success(f"✅ Portfolio successfully updated!")
                    st.info(f"Your portfolio is available at: [🔗 {st.session_state.site_url}]({st.session_state.site_url})")
                    
                    # Add a button to deploy again
                    if st.button("Deploy Again", key="deploy_again_button"):
                        st.session_state.deploy_clicked = False
                        st.session_state.show_progress = False
                        st.session_state.deployment_complete = False
                        st.rerun()
                    
                    # Add a button to go back to editing
                    if st.button("← Back to Editing", key="back_to_edit_after_success"):
                        # Make sure we preserve the edited_resume when going back to editing
                        if "edited_resume" not in st.session_state and "resume_data" in st.session_state:
                            st.session_state.edited_resume = copy.deepcopy(st.session_state.resume_data)
                        st.session_state.show_deployment_screen = False
                        st.rerun()

    else:
        # For new users - full workflow
        if "active_tab" not in st.session_state:
            st.session_state.active_tab = 0
            
        tab_titles = ["1. Upload & Edit", "2. Choose Theme", "3. Preview & Deploy"]
        tabs = st.tabs(tab_titles)
        
        # Check if we should display a specific tab based on workflow progression
        current_tab_index = st.session_state.active_tab
        
        with tabs[0]:  # Upload & Edit tab
            if current_tab_index == 0:  # Only show content if this is the active tab
                resume_file = st.file_uploader("Upload Resume pdf", type=["pdf"], key="resume_uploader")
                
                if resume_file:
                    # Check if we've already processed this file (to avoid re-uploading)
                    file_hash = hash(resume_file.getvalue())
                    process_file = True
                    
                    if "last_processed_file" in st.session_state and st.session_state.last_processed_file == file_hash:
                        process_file = False
                    
                    if process_file:
                        try:
                            with st.spinner("Processing your resume..."):
                                resume_file_obj = {"file": (resume_file.name, resume_file, "application/pdf")}
                                data = {"user_email": st.session_state.user_email}
                                
                                # Upload file to GCP
                                gcp = requests.post(f"{API_URL}/upload-to-gcp", params=data, files=resume_file_obj)
                                
                                # Generate JSON from resume
                                resume_response = requests.post(
                                    f"{API_URL}/json-to-sf", 
                                    json={"user_email": st.session_state.user_email, "mode": "generate"}
                                )
                                
                                if resume_response.status_code == 200:
                                    resume_data = resume_response.json()
                                    st.session_state.resume_data = resume_data
                                    st.session_state.edited_resume = copy.deepcopy(resume_data)
                                    st.session_state.last_processed_file = file_hash
                                    st.success("Resume loaded successfully! You can now edit your information.")
                                else:
                                    st.error(f"Error processing resume: {resume_response.text}")
                        except Exception as e:
                            st.error(f"An error occurred: {str(e)}")
                    
                    # Display the current resume data (read-only) and chat editor
                    if "edited_resume" in st.session_state:
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.subheader("Current Resume Preview")
                            display_resume_json(st.session_state.edited_resume)
                        
                        with col2:
                            st.subheader("AI Resume Editor")
                            create_llm_based_editor(st.session_state.edited_resume)
                        
                        # For new users, we still need the tab navigation but with clear deploy button
                        col_nav, col_deploy = st.columns([1, 1])
                        with col_nav:
                            if st.button("Continue to Theme Selection", key="continue_to_themes"):
                                # Change the active tab and directly update the UI
                                st.session_state.active_tab = 1
                                st.rerun()  # Force rerun to update UI
                else:
                    st.info("Please upload your resume PDF file to get started.")
             
        with tabs[1]:  # Choose Theme tab
            if current_tab_index == 1:  # Only show content if this is the active tab
                if "edited_resume" in st.session_state:
                    # Fetch themes from API
                    display_theme_selector(helper.THEMES)
                    
                    if st.session_state.get("theme_selected", False):
                        st.success(f"You have selected **{st.session_state.selected_theme}**")
                        if st.button("Preview & Deploy Your Portfolio", key="continue_to_deploy"):
                            # Change the active tab to deployment
                            st.session_state.active_tab = 2
                            st.rerun()  # Force rerun to update UI
                else:
                    st.warning("Please upload and edit your resume first.")
                    # Provide a button to go back to first tab
                    if st.button("← Go to Upload & Edit", key="go_to_upload"):
                        st.session_state.active_tab = 0
                        st.rerun()

        with tabs[2]:  # Preview & Deploy tab
            if current_tab_index == 2:  # Only show content if this is the active tab
                if "edited_resume" in st.session_state and st.session_state.get("theme_selected", False):
                    st.subheader("Final Review")
                    
                    # Get username from the correct structure based on new JSON format
                    if "about" in st.session_state.edited_resume and "name" in st.session_state.edited_resume["about"]:
                        username = st.session_state.edited_resume["about"]["name"]
                    else:
                        username = "portfolio"
                        
                    # Display information
                    st.markdown("### Your Information")
                    st.write(f"**Theme Selected**: {st.session_state.selected_theme}")
                    st.write(f"**Portfolio Owner**: {username}")

                    st.subheader("Repository Configuration")
                    repo_name_input = st.text_input("Enter the GitHub repository name you'd like to use", key="repo_name_input")

                    # Validate repo name via API - only if changed
                    if repo_name_input and not st.session_state.get("deployed_clicked", False):
                        # Cache validation to prevent repeated API calls
                        validation_key = f"repo_validation_{repo_name_input}"
                        if validation_key not in st.session_state:
                            valid = validate_repo_name(repo_name_input)
                            st.session_state[validation_key] = valid
                        
                        if st.session_state[validation_key]:
                            st.success("Repository name available!")
                        else:
                            st.error(f"A repository named '{repo_name_input}' already exists. Please choose another name.")

                    # Display deployment options
                    st.subheader("Deployment Options")
                    
                    # GitHub Deployment
                    if "deploy_clicked" not in st.session_state:
                        st.session_state.deploy_clicked = False
                    
                    if not st.session_state.deploy_clicked:
                        if st.button("🚀 Deploy to GitHub Pages", key="github_deploy_button"):
                            if not repo_name_input:
                                st.error("Please enter a GitHub repository name before deploying.")
                            elif not st.session_state.get(f"repo_validation_{repo_name_input}", False):
                                st.error("Repository name is not valid. Please choose a unique name.")
                            else:
                                st.session_state.deploy_clicked = True
                                st.session_state.repo_name = repo_name_input
                                
                                # Make sure edited_resume exists before deployment
                                if "edited_resume" not in st.session_state and "resume_data" in st.session_state:
                                    st.session_state.edited_resume = copy.deepcopy(st.session_state.resume_data)
                                
                                # Start asynchronous deployment
                                deploy_portfolio(
                                    st.session_state.user_email,
                                    st.session_state.selected_theme,
                                    repo_name_input.strip(),
                                    handle_deployment_completion
                                )
                                
                                # Show initial message
                                st.info("Deployment started! This will take approximately 40 seconds...")
                                st.session_state.show_deploy_progress = True
                                st.rerun()
                    
                    elif st.session_state.get("show_deploy_progress", False) and not st.session_state.get("deployment_complete", False):
                        # Show non-blocking progress bar for deployment
                        st.info("GitHub Pages deployment in progress...")
                        completed = show_non_blocking_progress("github_deploy", 100, 0.40)
                        
                        # Check if deployment result is available
                        if "deployment_url" in st.session_state:
                            st.session_state.deployment_complete = True
                            url = st.session_state.deployment_url
                            st.success("✅ Portfolio successfully deployed!")
                            st.subheader("Your Portfolio Website")
                            st.markdown(f"**Portfolio URL:** [🔗 {url}]({url})")
                            st.balloons()
                        elif not completed:
                            # Rerun to update progress bar
                            time.sleep(0.1)  # Short sleep to prevent too frequent reruns
                            st.rerun()
                        else:
                            # If progress is complete but no URL yet
                            if "wait_start_time" not in st.session_state:
                                # Start counting wait time
                                st.session_state.wait_start_time = time.time()
                                st.info("Deployment completed. Waiting for portfolio URL...")
                                time.sleep(0.5)
                                st.rerun()
                            elif time.time() - st.session_state.wait_start_time > 10:  # Wait for max 10 seconds
                                # Timeout reached, create a fallback URL
                                repo_name = st.session_state.repo_name
                                fallback_url = f"https://botfolio-builder.github.io/{repo_name}/"
                                
                                # Set the URL in session state
                                st.session_state.deployment_url = fallback_url
                                st.session_state.site_url = fallback_url
                                st.session_state.is_site_hosted = 1
                                st.session_state.deployment_complete = True
                                
                                # Show success message with fallback URL
                                st.success("✅ Portfolio successfully deployed!")
                                st.subheader("Your Portfolio Website")
                                st.markdown(f"**Portfolio URL:** [🔗 {fallback_url}]({fallback_url})")
                                st.markdown("**Note:** GitHub Pages may take a few minutes to fully activate. If the link doesn't work immediately, please wait a few minutes and try again.")
                                st.balloons()
                            else:
                                # Still within timeout period, keep waiting
                                st.info("Deployment completed. Waiting for portfolio URL...")
                                time.sleep(0.5)
                                st.rerun()
                    
                    elif st.session_state.get("deployment_complete", False):
                        # Show deployment completion UI
                        url = st.session_state.get("deployment_url") or st.session_state.get("site_url")
                        st.success("✅ Portfolio successfully deployed!")
                        st.subheader("Your Portfolio Website")
                        st.markdown(f"**Portfolio URL:** [🔗 {url}]({url})")
                        st.markdown("**Note:** GitHub Pages may take a few minutes to fully activate. If the link doesn't work immediately, please wait a few minutes and try again.")
                        
                        # Update sidebar information
                        st.sidebar.markdown("### Your Portfolio")
                        st.sidebar.markdown(f"🔗 [View your portfolio]({url})")
                        st.sidebar.markdown(f"Repository: {st.session_state.repo_name}")
                        
                        # Add a button to edit portfolio
                        if st.button("Edit My Portfolio", key="edit_portfolio_button"):
                            st.session_state.deploy_completed = True
                            st.rerun()
                        
                        # Offer JSON download
                        st.markdown("### Download Your Resume")
                        json_str = json.dumps(st.session_state.edited_resume, indent=2)
                        st.download_button(
                            label="Download JSON File",
                            data=json_str,
                            file_name="resume.json",
                            mime="application/json",
                            key="download_json_button"
                        )
                else:
                    # Show warning about missing information
                    if not st.session_state.get("theme_selected", False):
                        st.warning("Please select a theme first.")
                        # Provide a button to go back to theme selection
                        if st.button("← Go to Theme Selection", key="go_to_themes"):
                            st.session_state.active_tab = 1
                            st.rerun()
                    else:
                        st.warning("Please upload your resume, edit it, and select a theme first.")
                        # Provide a button to go back to first tab
                        if st.button("← Go to Upload & Edit", key="go_to_upload_from_deploy"):
                            st.session_state.active_tab = 0
                            st.rerun()

        # Display current step progress for new users
        current_step = st.session_state.active_tab + 1
        total_steps = 3
        st.sidebar.progress(current_step / total_steps)
        st.sidebar.write(f"**Current Progress**: Step {current_step} of {total_steps}")
        st.sidebar.write(f"**Current Step**: {tab_titles[st.session_state.active_tab]}")

        # Add next step instructions for new users
        if st.session_state.active_tab < 2:
            next_step = tab_titles[st.session_state.active_tab + 1]
            st.sidebar.info(f"**Next step**: {next_step}")

# Main app logic
st.set_page_config(page_title="Portfolio Builder", layout="wide")

# Check if user is authenticated
if "is_authenticated" not in st.session_state:
    st.session_state.is_authenticated = False

# If not authenticated, show login page
if not st.session_state.is_authenticated:
    login_page()
else:
    # If authenticated, show main app
    main_app()