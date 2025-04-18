from fastapi import FastAPI, File, UploadFile, HTTPException
from utils.resume_parser.core import *
from utils.gcp.cloud_storage import upload_file, upload_json, generate_signed_url, get_gcp_credentials
import os 
from utils.resume_parser.core import * 
from google.oauth2 import service_account
from google.cloud import storage
from uuid import uuid4
from pydantic import BaseModel
from utils.snowflake.snowflake_connector import get_this_column, update_this_column, request_to_signup
from utils.theme_compilation.core import render_html
from typing import Optional
import json 
import logging
import uvicorn

app = FastAPI()
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
load_dotenv()
BUCKET_NAME = os.getenv("GCP_RESUME_BUCKET_NAME")
 
secrets_json = get_gcp_credentials()
credentials = service_account.Credentials.from_service_account_info(secrets_json)
client = storage.Client(credentials=credentials)


class jsonModel(BaseModel):
    changes : Optional[str] = None
    mode : str
    user_email : str

class loginModel(BaseModel):
    user_email : str
    password : str

class signupModel(BaseModel):
    fullname: str
    user_email: str
    profession: str

class CompileRequest(BaseModel):
    user_email: str
    theme: str
 
@app.post("/resume-to-gcp/")
async def text_to_json_converter(user_email: str, file: UploadFile = File(...) ):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PDF file.")
    if not user_email:
        raise HTTPException(status_code=400, detail='Bad Request')
    try:
        id = uuid4()
        file_data = file.file
        content_type = file.content_type
        result = upload_file(file_data, f"uploads/{id}.pdf", content_type, credentials)

        presigned_url = generate_signed_url(BUCKET_NAME, f"uploads/{id}.pdf", credentials )
        update_this_column(user_email, 'resume_pdf_url', presigned_url)
        return presigned_url   
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.post("/json-to-sf/")
async def json_to_snowflake(requests : jsonModel):
    
    try:
        user_email = requests.user_email
        mode = requests.mode
        changes = getattr(requests, 'changes', None)
        json_data = get_structured_data(user_email, changes, mode)
        update_this_column(user_email, 'resume_json', json.dumps(json_data))
        return  json_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


@app.post("/login/")
async def login_user_if_exist(requests: loginModel):
  
    try:
        user_email = requests.user_email
        user_password = requests.password
        response = get_this_column(user_email,"PASSWORD")
        if user_password == response: 
            return {"statuscode" : 200, "message":"Login successfull"}  
        else: 
            return {"statuscode":401, "message":"Invalid username or password"}
            
    except Exception as e:
        return str(e)

@app.post("/signup/")
async def user_signup(requests : signupModel):
    try:
        fullname=requests.fullname
        user_email=requests.user_email
        profession=requests.profession
        response = request_to_signup(user_email, fullname, profession)
        if response != 0:
            return {"statuscode" : 200, "message":"User request successfull"}
        
        else:
            return {"statuscode" : 400, "message":"User already requested for account"}

    except Exception as e:
        return str(e)


@app.post("/compile")
async def compile_html(request: CompileRequest):
    user_email = request.user_email
    theme = request.theme
    with open('utils/theme_compilation/resume_mock.json', 'r') as f:
        resume_dict = json.loads(f.read())
    content = render_html(resume_dict, theme)
    return {'status_code':200, 'content':content}
        
        