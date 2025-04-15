import PyPDF2
import pdfplumber
import fitz
from typing import TypedDict, Optional, Dict
from dotenv import load_dotenv 
import json
from utils.litellm.core import llm
from utils.helper import * 
import requests
from io import BytesIO
import google.generativeai as genai
from utils.schema import *
import os
from utils.snowflake.snowflake_connector import *
import logging

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO)

def extract_text_from_pdf(content):
        """Extract text from PDF file using pdfplumber for better text extraction"""
        hyperlinks = []
        text = ""
        try:

            pdf_stream = BytesIO(content)
            # Use pdfplumber for better formatting preservation
            with pdfplumber.open(pdf_stream) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text(x_tolerance=3, y_tolerance=3)
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            print(f"Error extracting text from PDF: {str(e)}")

        try:
            doc = fitz.open(stream=content, filetype="pdf")
            for page_num, page in enumerate(doc):
                link_list = page.get_links()
                for link in link_list:
                    if link.get("uri"):
                        # Get the rectangle containing the link
                        rect = link.get("from")
                        
                        # Extract the text in this rectangle if available
                        link_text = ""
                        if rect:
                            words = page.get_text("words", clip=rect)
                            link_text = " ".join([word[4] for word in words]) if words else ""
                        
                        hyperlinks.append({
                            link_text : link.get("uri")
                        })
            doc.close()
        except Exception as e:
            print(f"PyMuPDF link extraction error: {str(e)}")

        
        return {"text" : text ,
                "links": hyperlinks}




def get_structured_data(user_email, changes, mode='generate'):
    """
    Get Structured JSON using text and links with Gemini API
    """
    # Configure the Gemini API
    logging.info('calling get structured data - ', changes, mode)
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    try:
        # Extract text
        if mode=='generate':
            pdf_url = get_this_column(user_email, 'resume_pdf_url')
            response = requests.get(pdf_url)
            data = extract_text_from_pdf(response.content) 
        else:
            data = get_this_column(user_email, 'resume_json')
        logging.info(data)
        # Create model and chat
        model = genai.GenerativeModel(
        model_name="gemini-1.5-pro",
        generation_config=generation_config,
        system_instruction=sys_resume_generate_prompt if mode == 'generate' else sys_resume_revise_prompt
        ) 
     
        chat = model.start_chat(history=[])
        
        # Send message and get response

        response = chat.send_message(user_resume_generate_prompt.format(data) if mode=='generate' else user_resume_revise_prompt.format(data, changes))
        response_text = response.text.strip()

        # Handle formatting
        if response_text.startswith("```json"):
            response_text = response_text.split("```json")[1]
        if "```" in response_text:
            response_text = response_text.split("```")[0]
        
        # Parse JSON
        cleaned_content = json.loads(response_text.strip())
        return cleaned_content
        
    except Exception as e:
        return {"error structuring": str(e)}