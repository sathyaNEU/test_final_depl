import os
import json
# from github import Github
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from dotenv import load_dotenv
import requests
import tempfile
import copy
import google.generativeai as genai
import time
from utils.theme_compilation.helper import THEMES, workflow
import logging
from github import Github, GithubException
from fastapi import HTTPException

load_dotenv()


GITHUB_TOKEN= os.getenv('GITHUB_TOKEN')
GITHUB_USERNAME = os.getenv('GITHUB_USERNAME')


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Template directory
TEMPLATE_DIR = Path(__file__).parent.parent / "theme_compilation" / "templates"


def render_html(resume_dict, template_file):
    """Render HTML template with resume data"""
    try:
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        template = env.get_template(THEMES[template_file]['file'])      
        return template.render(resume=resume_dict)
    except Exception as e:
        raise HTTPException(status_code=404,detail="Theme not found")


# def check_repo_exists(repo_name: str):
#     g = Github(GITHUB_TOKEN)
#     try:
#         g.get_user().get_repo(repo_name)
#         return True
#     except:
#         return False


def check_repo_exists(repo_name: str):
    g = Github(GITHUB_TOKEN)
    try:
        g.get_user().get_repo(repo_name)
        return True
    except GithubException as e:
        return False
    


def create_github_repo(repo_name, html_content, is_deployed=False):
    """Create and deploy GitHub repository with portfolio"""
    g = Github(GITHUB_TOKEN)
    user = g.get_user()
    
    try:
        # Check if we're updating an existing repo or creating a new one
        if is_deployed:
            # Updating existing repo
            try:
                repo = user.get_repo(repo_name)
                
                # Update files
                try:
                    contents = repo.get_contents("index.html")
                    repo.update_file("index.html", "Update portfolio page", html_content, contents.sha, branch="main")
                except:
                    repo.create_file("index.html", "Add portfolio page", html_content, branch="main")
                               
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
                time.sleep(4)
            except:
                # Repo might exist, get it instead
                repo = user.get_repo(repo_name)
            
            # Add files
            try:
                contents = repo.get_contents("index.html")
                repo.update_file("index.html", "Update portfolio page", html_content, contents.sha, branch="main")
            except:
                repo.create_file("index.html", "Add portfolio page", html_content, branch="main")
                    
            # Add .nojekyll file if not exists
            try:
                repo.get_contents(".nojekyll")
            except:
                repo.create_file(".nojekyll", "Disable Jekyll processing", "", branch="main")
        
        # Add GitHub Pages workflow        
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
