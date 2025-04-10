from fastapi import FastAPI, File, UploadFile, HTTPException
from utils.resume_parser.core import *
from utils.gcp.cloud_storage import upload_file, upload_json, generate_signed_url, get_gcp_credentials
import os 
from utils.resume_parser.core import * 
from google.oauth2 import service_account
from google.cloud import storage


app = FastAPI()

load_dotenv()
BUCKET_NAME = os.getenv("GCP_RESUME_BUCKET_NAME")
 
secrets_json = get_gcp_credentials()
credentials = service_account.Credentials.from_service_account_info(secrets_json)
client = storage.Client(credentials=credentials)

 
@app.post("/resume-to-json/")
async def text_to_json_converter(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PDF file.")
    
    try:
        file_data = file.file
        filename = file.filename.split(".")[0]
        content_type = file.content_type
        result = upload_file(file_data, f"{filename}/{filename}.pdf", content_type, credentials)

        presigned_url = generate_signed_url(BUCKET_NAME, f"{filename}/{filename}.pdf", credentials )
        json_data = get_structured_data(presigned_url)
        response =  upload_json(json_data, f"{filename}/{filename}.json", credentials) 

        # print(f"response:{response}")
        return response   
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

