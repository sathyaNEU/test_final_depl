from datetime import datetime
from airflow.models import Variable
from google import genai
from google.genai import types
import base64
from google import genai
from google.genai import types
import base64
from utils.llm.prompt import sys_skill_extract_prompt
import json
from airflow.hooks.base import BaseHook
from google.oauth2 import service_account
import google.auth.transport.requests


import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

def get_vertexai_credentials(gcp_conn_id="vertex-ai"):
    connection = BaseHook.get_connection(gcp_conn_id)
    keyfile_dict = connection.extra_dejson.get("keyfile_dict")
    if keyfile_dict:
        # Parse keyfile_dict if it's a string
        if isinstance(keyfile_dict, str):
            keyfile_dict = json.loads(keyfile_dict)
            
        # Use standard scopes for API access
        scopes = ["https://www.googleapis.com/auth/cloud-platform"]
        
        # Create credentials with explicit token_uri
        credentials = service_account.Credentials.from_service_account_info(
            keyfile_dict, 
            scopes=scopes
        )
        
        # Force token refresh to ensure we have a valid access token
        request = google.auth.transport.requests.Request()
        credentials.refresh(request)
        
        return credentials
    else:
        raise ValueError("Missing 'keyfile_dict' in connection extras")
    


def llm(description):
  credentials = get_vertexai_credentials()

  logging.info(credentials)

  client = genai.Client(
      vertexai=True,
      project="bigdata-456820",
      location="us-central1",
      credentials=credentials
  )
 
  model = "gemini-2.0-flash-001"
  contents = [
    types.Content(
      role="user",
      parts=[
        types.Part.from_text(text=description)
      ]
    ),
  ]
  generate_content_config = types.GenerateContentConfig(
    temperature = 1,
    top_p = 0.95,
    max_output_tokens = 8192,
    response_modalities = ["TEXT"],
    safety_settings = [types.SafetySetting(
      category="HARM_CATEGORY_HATE_SPEECH",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_DANGEROUS_CONTENT",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_HARASSMENT",
      threshold="OFF"
    )],
    response_mime_type = "application/json",
    system_instruction=[types.Part.from_text(text=sys_skill_extract_prompt)],
  )
 
  response = client.models.generate_content(
    model = model,
    contents = contents,
    config = generate_content_config,
    )
  
  result =response.text
  data = json.loads(result)

  
  return data['technical_skills']
  