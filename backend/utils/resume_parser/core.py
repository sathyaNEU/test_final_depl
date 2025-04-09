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


load_dotenv()

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



def get_structured_data(url):
    """
    Get Structured JSON using text and links 
    """

    response = requests.get(url)
    pdf_content = response.content

    try:
        data = extract_text_from_pdf(pdf_content)
        prompt = prompt_for_json(data)

        response = llm("gemini/gemini-1.5-pro",prompt)
        cleaned_content = json.loads(response['answer'])
        
        return cleaned_content
    
    except Exception as e:
        return str(e)