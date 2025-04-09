from fastapi import FastAPI, File, UploadFile, HTTPException
from utils.resume_parser.core import *
from utils.gcp.cloud_storage import upload_file, upload_json
import os 
from utils.resume_parser.core import * 
from google.cloud import storage
from google.oauth2 import service_account
from datetime import timedelta





app = FastAPI()

load_dotenv()
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
BUCKET_NAME = os.getenv("GCP_RESUME_BUCKET_NAME")
credentials = service_account.Credentials.from_service_account_file('gcpkeys.json')

def generate_signed_url(bucket_name, object_name):
    client = storage.Client(credentials=credentials)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_name)

    url = blob.generate_signed_url(
        expiration=timedelta(hours=24),
        method='GET'
    )
    return url

@app.post("/resume-to-json/")
async def text_to_json_converter(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PDF file.")
    
    try:
        file_data = file.file
        filename = file.filename.split(".")[0]
        content_type = file.content_type
        result = upload_file(file_data, f"{filename}/{filename}.pdf", content_type )

        presigned_url = generate_signed_url(BUCKET_NAME, f"{filename}/{filename}.pdf" )
        json_data = get_structured_data(presigned_url)
        response =  upload_json(json_data, f"{filename}/{filename}.json") 

        # print(f"response:{response}")
        return response   
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

