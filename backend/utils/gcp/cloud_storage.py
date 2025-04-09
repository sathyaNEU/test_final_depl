from google.cloud import storage
from dotenv import load_dotenv
import os 
import json

load_dotenv()
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
BUCKET_NAME = os.getenv("GCP_RESUME_BUCKET_NAME")
client = storage.Client()

def upload_file(file_data, filename, content_type):
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_file(file_data, content_type=content_type)
    return {"message": f"File '{filename}' uploaded successfully to bucket '{BUCKET_NAME}'."}


def upload_json(data, filename):
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(
        data= json.dumps(data), 
        content_type="application/json")
    return {"message": f"File '{filename}' uploaded successfully to bucket '{BUCKET_NAME}'."}
