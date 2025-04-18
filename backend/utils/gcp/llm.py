from google import genai
from google.genai import types
import base64
import json
from utils.schema import validate_qa_data
from utils.helper import sys_qa_validation_prompt, user_qa_validation_prompt
from google import genai
from google.genai import types
from google import genai
from google.oauth2 import service_account
import google.auth.transport.requests
from utils.schema import validate_qa_data
from google.oauth2 import service_account
from google.cloud import secretmanager
import os
from dotenv import load_dotenv
from google.oauth2 import service_account

load_dotenv()


def judge_qa(combined_qa):
    client = genai.Client(
      vertexai=True,
      project="botfolio-456006",
      location="us-central1",
    #   credentials=credentials
      
    )
 
    model = "gemini-2.5-pro-exp-03-25"
    contents = [
    types.Content(
        role="user",
        parts=[
        types.Part.from_text(text=user_qa_validation_prompt.format(combined_qa))
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
    system_instruction=[types.Part.from_text(text=sys_qa_validation_prompt)],
    )
 
    response = client.models.generate_content(
    model = model,
    contents = contents,
    config = generate_content_config,
    ).candidates[0].content.parts[0].text
    response_dict = json.loads(response)
    wrapped_response = {"reviews": response_dict}
    validated_data = validate_qa_data(wrapped_response)
    if isinstance(validated_data, list) and len(validated_data)==0:
        return -1
    return validated_data['reviews']