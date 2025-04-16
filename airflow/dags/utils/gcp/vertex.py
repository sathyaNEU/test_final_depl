from google import genai
from google.genai import types
import base64
import json
from utils.prompts import sys_qa_datagen_prompt, user_qa_datagen_prompt
from utils.schema import validate_qa_data
from dotenv import load_dotenv
from airflow.hooks.base import BaseHook
from google.oauth2 import service_account
import google.auth.transport.requests
load_dotenv()

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

def generate_qa(site_as_md):
    client = genai.Client(
      vertexai=True,
      project="directed-asset-456902-a9",
      location="us-central1",
      credentials = get_vertexai_credentials()
    )

    model = "gemini-2.5-pro-exp-03-25"
    contents = [
    types.Content(
      role="user",
      parts=[
        types.Part.from_text(text=user_qa_datagen_prompt.format(site_as_md))
      ]
    ),
    ]
    generate_content_config = types.GenerateContentConfig(
        temperature = 1,
        top_p = 0.95,
        max_output_tokens = 30000,
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
        system_instruction=[types.Part.from_text(text=sys_qa_datagen_prompt)],
    )

    response = client.models.generate_content(
        model = model,
        contents = contents,
        config = generate_content_config,
    )
    response_json = json.loads(response.candidates[0].content.parts[0].text)
    validated_data = validate_qa_data(response_json)
    if isinstance(validated_data, list) and len(validated_data)==0:
        return -1
    if 'qa_pairs' not in validated_data:
        return -1     
    return validated_data['qa_pairs']