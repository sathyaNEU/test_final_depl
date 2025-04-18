from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Union, Any
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
import os
import json
import uuid
import hashlib
from datetime import datetime, timedelta
import jwt
from github import Github
from dotenv import load_dotenv
import requests
import time

# Load environment variables
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")

# Constants
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey123")  # Should be properly secured in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# FastAPI app
app = FastAPI(title="Portfolio Generator API", 
              description="Backend API for the Portfolio Generator application",
              version="1.0.0")

# Add CORS middleware to allow Streamlit to communicate with the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your Streamlit app's URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OAuth2 for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Template directory
TEMPLATE_DIR = Path(__file__).parent / "templates"

# Mock database (replace with a real database in production)
USER_DB = {
    "dummy@gmail.com": {
        "password": hashlib.sha256("password123".encode()).hexdigest(),
        "is_site_hosted": 0,
        "site_url": None,
        "repo_name": None,
        "theme": None,
        "resume_data": None
    },
    "test@example.com": {
        "password": hashlib.sha256("test123".encode()).hexdigest(),
        "is_site_hosted": 1,
        "site_url": "https://username.github.io/test-portfolio/",
        "repo_name": "test-portfolio",
        "theme": "Theme 2",
        "resume_data": {
            "about": {
                "name": "Test User",
                "location": "San Francisco, CA",
                "email": "test@example.com",
                "phone": "+1-555-123-4567",
                "linkedin_hyperlink": "https://linkedin.com/in/testuser",
                "github_hyperlink": "https://github.com/testuser",
                "summary": "Experienced developer with a passion for building web applications."
            },
            "education": [
                {
                    "university": "Stanford University",
                    "location": "Stanford, CA",
                    "degree": "Bachelor of Science in Computer Science",
                    "period": "Sep 2016 - Jun 2020",
                    "related_coursework": ["Algorithms", "Data Structures", "Web Development"],
                    "gpa": "3.8"
                }
            ],
            "skills": [
                {
                    "category": "Programming Languages",
                    "skills": ["JavaScript", "Python", "Java"]
                }
            ],
            "experience": [
                {
                    "company": "Tech Company",
                    "position": "Software Engineer",
                    "location": "Remote",
                    "period": "Jul 2020 - Present",
                    "responsibilities": ["Developed web applications using React and Node.js"]
                }
            ],
            "projects": [
                {
                    "name": "Portfolio Generator",
                    "description": "Web application that generates portfolio websites from resume data",
                    "technologies": ["Python", "Streamlit", "GitHub API"],
                    "url": "https://github.com/testuser/portfolio-generator"
                }
            ],
            "accomplishments": [
                {
                    "title": "Best Developer Award",
                    "date": "Jun 2022",
                    "link": "https://example.com/award"
                }
            ]
        }
    }
}

# Define the available themes
THEMES = {
    "Theme 1": {
        "file": "theme1.html",
        "description": "Modern dark blue theme with teal accents. Professional design with card-based layout."
    },
    "Theme 2": {
        "file": "theme2.html",
        "description": "Vibrant purple/pink gradient design. Creative layout with timeline experience section."
    },
    "Theme 3": {
        "file": "theme3.html",
        "description": "Clean, light theme with teal/amber accents. Minimal and elegant professional style."
    },
    "Theme 4": {
        "file": "theme4.html",
        "description": "Bold slate blue with red accents. Interactive design with modern visual elements."
    }
}

# Pydantic models
class Token(BaseModel):
    access_token: str
    token_type: str
    
class TokenData(BaseModel):
    email: Optional[str] = None
    
class User(BaseModel):
    email: str
    is_site_hosted: int
    site_url: Optional[str] = None
    repo_name: Optional[str] = None
    theme: Optional[str] = None

class UserCreate(BaseModel):
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class DeployRequest(BaseModel):
    repo_name: str
    theme: str
    resume_data: Dict[str, Any]

class ResumeUpdate(BaseModel):
    resume_data: Dict[str, Any]

class ThemeSelection(BaseModel):
    theme: str
    
class RepoNameRequest(BaseModel):
    repo_name: str

# Functions for authentication
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
        return token_data
    except jwt.PyJWTError:
        raise credentials_exception

def get_current_user(token_data: TokenData = Depends(verify_token)):
    user = USER_DB.get(token_data.email)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return token_data.email

def verify_password(plain_password: str, hashed_password: str):
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password

def get_user(email: str):
    if email in USER_DB:
        user_data = USER_DB[email].copy()
        del user_data["password"]  # Don't return the password
        return user_data
    return None

def render_html(resume_json, template_file):
    """Render HTML template with resume data"""
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template(template_file)
    return template.render(resume=resume_json)

def create_github_repo(repo_name, html_content, resume_json, template_file, is_update=False):
    """Create and deploy GitHub repository with portfolio"""
    g = Github(GITHUB_TOKEN)
    user = g.get_user()
    
    try:
        # Check if we're updating an existing repo or creating a new one
        if is_update:
            # Updating existing repo
            try:
                repo = user.get_repo(repo_name)
                
                # Update files
                try:
                    contents = repo.get_contents("index.html")
                    repo.update_file("index.html", "Update portfolio page", html_content, contents.sha, branch="main")
                except:
                    repo.create_file("index.html", "Add portfolio page", html_content, branch="main")
                
                # Update resume JSON
                resume_bytes = json.dumps(resume_json, indent=2).encode("utf-8")
                try:
                    contents = repo.get_contents("resume.json")
                    repo.update_file("resume.json", "Update resume JSON", resume_bytes.decode(), contents.sha, branch="main")
                except:
                    repo.create_file("resume.json", "Add resume JSON", resume_bytes.decode(), branch="main")
                    
                # Add .nojekyll file if not exists
                try:
                    repo.get_contents(".nojekyll")
                except:
                    repo.create_file(".nojekyll", "Disable Jekyll processing", "", branch="main")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error updating repository: {str(e)}")
        else:
            # Creating new repo
            try:
                repo = user.create_repo(repo_name, private=False, auto_init=True)
                # Wait briefly for repo initialization
                time.sleep(2)
            except:
                # Repo might exist, get it instead
                repo = user.get_repo(repo_name)
            
            # Add files
            try:
                contents = repo.get_contents("index.html")
                repo.update_file("index.html", "Update portfolio page", html_content, contents.sha, branch="main")
            except:
                repo.create_file("index.html", "Add portfolio page", html_content, branch="main")
            
            # Add resume JSON
            resume_bytes = json.dumps(resume_json, indent=2).encode("utf-8")
            try:
                contents = repo.get_contents("resume.json")
                repo.update_file("resume.json", "Update resume JSON", resume_bytes.decode(), contents.sha, branch="main")
            except:
                repo.create_file("resume.json", "Add resume JSON", resume_bytes.decode(), branch="main")
                
            # Add .nojekyll file if not exists
            try:
                repo.get_contents(".nojekyll")
            except:
                repo.create_file(".nojekyll", "Disable Jekyll processing", "", branch="main")
        
        # Add GitHub Pages workflow
        workflow = """name: Deploy to GitHub Pages

on:
  push:
    branches: ["main"]
  workflow_dispatch:

permissions:
  contents: write
  pages: write
  id-token: write

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v3
      - name: Setup Pages
        uses: actions/configure-pages@v3
      - name: Build
        run: |
          echo "Building site..."

  report-build-status:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Report build status
        run: echo "Build completed successfully!"

  deploy:
    needs: report-build-status
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v3
      - name: Deploy to GitHub Pages
        uses: JamesIves/github-pages-deploy-action@v4
        with:
          folder: .
          branch: gh-pages
"""
        
        try:
            # Create workflows directory if it doesn't exist
            try:
                repo.get_contents(".github/workflows")
            except:
                try:
                    repo.create_file(".github/.gitkeep", "Create .github directory", "", branch="main")
                except:
                    pass
                try:
                    repo.create_file(".github/workflows/.gitkeep", "Create workflows directory", "", branch="main")
                except:
                    pass
                
            # Update or create workflow file
            try:
                contents = repo.get_contents(".github/workflows/deploy.yml")
                repo.update_file(".github/workflows/deploy.yml", "Update CI workflow", workflow, contents.sha, branch="main")
            except:
                try:
                    repo.create_file(".github/workflows/deploy.yml", "Add CI workflow", workflow, branch="main")
                except Exception as create_error:
                    pass
        except Exception:
            pass
        
        # Enable GitHub Pages - even if it returns a 422 error, continue with the process
        try:
            # First update repository settings
            settings_url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}"
            headers = {
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json"
            }
            settings_data = {
                "has_pages": True,
            }
            
            # Update repository settings to enable GitHub Pages
            requests.patch(settings_url, headers=headers, json=settings_data)
            
            # Try to configure GitHub Pages - first attempt with gh-pages branch
            pages_url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/pages"
            
            # Try multiple attempts with different configurations
            try:
                # First try gh-pages branch
                pages_data = {"source": {"branch": "gh-pages"}}
                requests.post(pages_url, headers=headers, json=pages_data)
            except:
                pass
                
            # Also try with main branch just to be safe
            try:
                pages_data = {"source": {"branch": "main"}}
                requests.post(pages_url, headers=headers, json=pages_data)
            except:
                pass
            
        except Exception:
            # Ignore GitHub Pages configuration errors
            pass

        # Always return the URL regardless of the GitHub Pages configuration status
        return f"https://{GITHUB_USERNAME}.github.io/{repo_name}/"
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error with repository: {str(e)}")

# Check if repo exists
def check_repo_exists(repo_name: str):
    g = Github(GITHUB_TOKEN)
    try:
        g.get_user().get_repo(repo_name)
        return True
    except:
        return False

# API Endpoints
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username not in USER_DB or not verify_password(form_data.password, USER_DB[form_data.username]["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/login")
async def login(login_data: LoginRequest):
    if login_data.email not in USER_DB or not verify_password(login_data.password, USER_DB[login_data.email]["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": login_data.email}, expires_delta=access_token_expires
    )
    
    user_data = get_user(login_data.email)
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user_data": user_data
    }

@app.post("/register")
async def register(user_data: UserCreate):
    if user_data.email in USER_DB:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash the password
    hashed_password = hashlib.sha256(user_data.password.encode()).hexdigest()
    
    # Create new user
    USER_DB[user_data.email] = {
        "password": hashed_password,
        "is_site_hosted": 0,
        "site_url": None,
        "repo_name": None,
        "theme": None,
        "resume_data": None
    }
    
    # Generate token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_data.email}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "message": "User registered successfully"
    }

@app.get("/user", response_model=Dict)
async def get_user_info(current_user: str = Depends(get_current_user)):
    user_data = get_user(current_user)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    return user_data

@app.get("/themes")
async def get_themes(current_user: str = Depends(get_current_user)):
    return THEMES

@app.post("/validate-repo")
async def validate_repository(request: RepoNameRequest, current_user: str = Depends(get_current_user)):
    repo_exists = check_repo_exists(request.repo_name)
    return {"valid": not repo_exists}

@app.post("/deploy")
async def deploy_portfolio(deploy_data: DeployRequest, current_user: str = Depends(get_current_user)):
    # Check if repo name is available (unless user is updating their own repo)
    is_update = USER_DB[current_user]["is_site_hosted"] == 1 and USER_DB[current_user]["repo_name"] == deploy_data.repo_name
    
    if not is_update and check_repo_exists(deploy_data.repo_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Repository name already exists. Please choose another name."
        )
    
    # Render HTML
    html = render_html(
        deploy_data.resume_data,
        THEMES[deploy_data.theme]["file"]
    )
    
    # Create or update GitHub repo
    url = create_github_repo(
        deploy_data.repo_name,
        html,
        deploy_data.resume_data,
        THEMES[deploy_data.theme]["file"],
        is_update
    )
    
    # Update user data
    USER_DB[current_user]["is_site_hosted"] = 1
    USER_DB[current_user]["site_url"] = url
    USER_DB[current_user]["repo_name"] = deploy_data.repo_name
    USER_DB[current_user]["theme"] = deploy_data.theme
    USER_DB[current_user]["resume_data"] = deploy_data.resume_data
    
    return {
        "status": "success",
        "message": "Portfolio deployed successfully",
        "url": url
    }

@app.put("/update-resume")
async def update_resume(resume_update: ResumeUpdate, current_user: str = Depends(get_current_user)):
    if USER_DB[current_user]["is_site_hosted"] == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User does not have a hosted portfolio yet"
        )
    
    USER_DB[current_user]["resume_data"] = resume_update.resume_data
    
    return {
        "status": "success",
        "message": "Resume updated successfully"
    }

@app.post("/select-theme")
async def select_theme(theme_selection: ThemeSelection, current_user: str = Depends(get_current_user)):
    if theme_selection.theme not in THEMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid theme selection"
        )
    
    return {
        "status": "success",
        "message": f"Theme {theme_selection.theme} selected successfully",
        "theme": THEMES[theme_selection.theme]
    }

@app.get("/")
async def root():
    return {"message": "Welcome to the Portfolio Generator API"}

# Run the application with uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)