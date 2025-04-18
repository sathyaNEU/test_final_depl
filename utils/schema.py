import os
import google.generativeai as genai
from google.ai.generativelanguage_v1beta.types import content
from pydantic import BaseModel, ValidationError
from typing import List
 

class QAReviewItem(BaseModel):
    id: int
    review: str
   
class QAValidationOutput(BaseModel):
    reviews: List[QAReviewItem]


def validate_qa_data(qa_response):
    try:
        # Attempt to validate and create a QAList object
        validated = QAValidationOutput(**qa_response)
        return validated.model_dump()  # Return the validated data as a dictionary
    except ValidationError:
        # If validation fails, return an empty list and handle appropriately in the calling function
        return []
 


def resume_json_schema():
 return  {
    "type": "object",
    "properties": {
        "about": {
        "type": "object",
        "properties": {
            "name": { "type": "string" },
            "location": { "type": "string" },
            "email": { "type": "string" },
            "phone": { "type": "string" },
            "linkedin_hyperlink": { "type": "string" },  #new
            "github_hyperlink": { "type": "string" },    #new
            "summary": { "type": "string" } #new
        },
        "required": ["name"]
        },
        "education": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
            "university": { "type": "string" },
            "location": { "type": "string" },
            "degree": { "type": "string" },
            "period": { "type": "string" },
            "related_coursework": {
                "type": "array",
                "items": { "type": "string" }
            },
            "gpa": { "type": "string" }
            },
            "required": ["university", "degree"]
        }
        },
        "skills": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
            "category": { "type": "string" },
            "skills": {
                "type": "array",
                "items": { "type": "string" }
            }
            },
            "required": ["category", "skills"]
        }
        },
        "experience": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
            "company": { "type": "string" },
            "position": { "type": "string" }, #new
            "location": { "type": "string" },
            "period": { "type": "string" },
            "responsibilities": {
                "type": "array",
                "items": { "type": "string" }
            }
            },
            "required": ["company", "position"]
        }
        },
        "projects": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
            "name": { "type": "string" },
            "description": { "type": "string" },
            "technologies": {
                "type": "array",
                "items": { "type": "string" }
            },
            "url": { "type": "string" }
            },
            "required": ["name", "description"]
        }
        },
        "accomplishments": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
            "title": { "type": "string" },
            "date": { "type": "string" },
            "link": { "type": "string" }
            }
        }
        }
    },
    "required": ["about", "education", "skills"]
    }

sys_resume_generate_prompt = f"""
        You are a structured data extractor specializing in interpreting raw data and organizing it into a defined structure. Your task is to process the provided raw information and return it in the exact format of the given resume schema.
        
        - Your response must strictly follow the structure outlined in the `resume_schema`.
        - The provided context will contain all the information you need. Do not generate new content or assume anything outside of what is provided.
        - Make sure all required fields from the schema are populated appropriately.
        - Respond using the defined structure of the schema, organizing the provided raw data into the correct sections.
        
        Ensure that the output strictly matches the resume format, as described in the schema, without any deviations.
    """


sys_resume_revise_prompt =f"""
        You are an AI designed to revise and update a resume based on user inputs. The user may provide new details or ask to modify sections in the resume.
        
        Your task is to intelligently process the request, identify the relevant section(s) of the resume to update, and make the appropriate changes while ensuring the structure of the resume remains consistent with the provided schema.
        
        Below is the schema that defines the required fields and structure of the resume:
        
        When revising the resume:
        1. Maintain the integrity of the existing sections.
        2. Ensure that any new information is incorporated in the appropriate section(s).
        3. If the user adds new details, ensure they follow the format and required fields.
        4. If the user provides instructions that conflict with the existing data, suggest appropriate ways to reconcile the changes (e.g., merging, updating, or adding additional information).
        5. Do not create new sections unless specified by the user; focus on modifying the current sections.
        
        Please process the user's request and update the resume accordingly.
        """

user_resume_generate_prompt = """
Here is the raw data for the resume. Please process this information and return the resume in the exact format as defined in the schema.
 
Context:
{}
 
Do not generate any new content. The resume should strictly reflect the provided raw data.
"""
 

 # first param - resume
# second param - user prompt
user_resume_revise_prompt = """
Here is the current version of the resume based on the schema:
 
{}
 
The user's request:
{}
 
Please revise the resume according to the provided instructions.
"""

generation_config = {
  "temperature": 1,
  "top_p": 0.95,
  "top_k": 40,
  "max_output_tokens": 8192,
  "response_schema": content.Schema(
    type = content.Type.OBJECT,
    required = ["about", "education", "skills"],
    properties = {
      "about": content.Schema(
        type = content.Type.OBJECT,
        required = ["name"],
        properties = {
          "name": content.Schema(
            type = content.Type.STRING,
          ),
          "location": content.Schema(
            type = content.Type.STRING,
          ),
          "email": content.Schema(
            type = content.Type.STRING,
          ),
          "phone": content.Schema(
            type = content.Type.STRING,
          ),
          "linkedin_hyperlink": content.Schema(
            type = content.Type.STRING,
          ),
          "github_hyperlink": content.Schema(
            type = content.Type.STRING,
          ),
          "summary": content.Schema(
            type = content.Type.STRING,
          ),
        },
      ),
      "education": content.Schema(
        type = content.Type.ARRAY,
        items = content.Schema(
          type = content.Type.OBJECT,
          required = ["university", "degree"],
          properties = {
            "university": content.Schema(
              type = content.Type.STRING,
            ),
            "location": content.Schema(
              type = content.Type.STRING,
            ),
            "degree": content.Schema(
              type = content.Type.STRING,
            ),
            "period": content.Schema(
              type = content.Type.STRING,
            ),
            "related_coursework": content.Schema(
              type = content.Type.ARRAY,
              items = content.Schema(
                type = content.Type.STRING,
              ),
            ),
            "gpa": content.Schema(
              type = content.Type.STRING,
            ),
          },
        ),
      ),
      "skills": content.Schema(
        type = content.Type.ARRAY,
        items = content.Schema(
          type = content.Type.OBJECT,
          required = ["category", "skills"],
          properties = {
            "category": content.Schema(
              type = content.Type.STRING,
            ),
            "skills": content.Schema(
              type = content.Type.ARRAY,
              items = content.Schema(
                type = content.Type.STRING,
              ),
            ),
          },
        ),
      ),
      "experience": content.Schema(
        type = content.Type.ARRAY,
        items = content.Schema(
          type = content.Type.OBJECT,
          required = ["company", "position"],
          properties = {
            "company": content.Schema(
              type = content.Type.STRING,
            ),
            "position": content.Schema(
              type = content.Type.STRING,
            ),
            "location": content.Schema(
              type = content.Type.STRING,
            ),
            "period": content.Schema(
              type = content.Type.STRING,
            ),
            "responsibilities": content.Schema(
              type = content.Type.ARRAY,
              items = content.Schema(
                type = content.Type.STRING,
              ),
            ),
          },
        ),
      ),
      "projects": content.Schema(
        type = content.Type.ARRAY,
        items = content.Schema(
          type = content.Type.OBJECT,
          required = ["name", "description"],
          properties = {
            "name": content.Schema(
              type = content.Type.STRING,
            ),
            "description": content.Schema(
              type = content.Type.STRING,
            ),
            "technologies": content.Schema(
              type = content.Type.ARRAY,
              items = content.Schema(
                type = content.Type.STRING,
              ),
            ),
            "url": content.Schema(
              type = content.Type.STRING,
            ),
          },
        ),
      ),
      "accomplishments": content.Schema(
        type = content.Type.ARRAY,
        items = content.Schema(
          type = content.Type.OBJECT,
          properties = {
            "title": content.Schema(
              type = content.Type.STRING,
            ),
            "date": content.Schema(
              type = content.Type.STRING,
            ),
            "link": content.Schema(
              type = content.Type.STRING,
            ),
          },
        ),
      ),
    },
  ),
  "response_mime_type": "application/json",
}