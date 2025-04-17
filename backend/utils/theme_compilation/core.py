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
from utils.theme_compilation.helper import THEMES
import logging
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
        print(str(e))
        return 'random'