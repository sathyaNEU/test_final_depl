from fastapi import FastAPI, File, UploadFile, HTTPException, status
from utils.resume_parser.core import *
from utils.gcp.cloud_storage import upload_file, upload_json, generate_signed_url, get_gcp_credentials
import os 
from utils.resume_parser.core import * 
from google.oauth2 import service_account
from google.cloud import storage
from uuid import uuid4
from pydantic import BaseModel
from utils.snowflake.snowflake_connector import get_this_column, update_this_column, request_to_signup
from utils.theme_compilation.core import render_html, check_repo_exists, create_github_repo
import json 
import logging
import uvicorn
from typing import Optional, List, Dict, Any
import pandas as pd
from dotenv import load_dotenv
import traceback
from datetime import datetime, timedelta
from utils.suggested_jobs.core import *


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

class compileModel(BaseModel):
    user_email: str
    theme: str
    repo_name :str

class RepoNameRequest(BaseModel):
    repo_name: str

class JobFilter(BaseModel):
        role: Optional[str] = None
        time_filter: Optional[str] = None
        seniority_level: Optional[str] = None
        employment_type: Optional[str] = None
        action: Optional[str] = None  
    
class InterviewPrepData(BaseModel):
        job_role: str
        skills: List[str]
        job_url: str
    
class JobsRequest(BaseModel):
        filter: Optional[JobFilter] = None
        interview_prep: Optional[InterviewPrepData] = None

JOBS_CACHE = {
        "data": None,
        "timestamp": None
    }

 
@app.post("/upload-to-gcp/")
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
        return {'status_code':200, 'url': presigned_url  }
    
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
        response = get_this_column(user_email,["PASSWORD", "RESUME_JSON", "UI_ENDPOINT", "THEME","NAME"])

        if user_password == response["PASSWORD"]: 
            return {"status_code" : 200, "message":"Login successfull", "user_data": response}  
        else: 
            return {"status_code":401, "message":"Invalid username or password"}
            
    except Exception as e:
        return str(e)

@app.post("/register/")
async def user_signup(requests : signupModel):
    try:
        fullname=requests.fullname
        user_email=requests.user_email
        profession=requests.profession
        response = request_to_signup(user_email, fullname, profession)
        if response != 0:
            return {"status_code" : 200, "message":"User request successfull"}
        
        else:
            return {"status_code" : 400, "message":"User already requested for account"}

    except Exception as e:
        return str(e)

@app.post("/compile")
async def compiler(requests : compileModel):
    try:
        user_email=requests.user_email
        theme=requests.theme
        resume_dict = json.loads(get_this_column(user_email, 'resume_json'))
        # logging.info(f"Parsed resume_dict: {type(resume_dict)} - {resume_dict}")
        compliled_html = render_html(resume_dict=resume_dict, template_file=theme)
        return  {"status_code" : 200, "message": compliled_html}
    except Exception as e:
        logging.info(str(e))
        return {"status_code" : 400, "message": 'Theme not found'}


@app.post("/validate-repo")
async def validate_repository(request: RepoNameRequest):
    repo_exists = check_repo_exists(request.repo_name)
    return {"valid": not repo_exists}

@app.post("/deploy")
async def deploy_portfolio(deploy_data: compileModel):
    try:
        # Extract values
        user_email = deploy_data.user_email
        theme = deploy_data.theme
        repo_name = deploy_data.repo_name
        is_deployed = False if get_this_column(user_email, "UI_ENDPOINT") is None else True

        # Check repo existence
        if not is_deployed and check_repo_exists(repo_name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Repository name already exists. Please choose another name."
            )

        # Render HTML
        resume_dict = json.loads(get_this_column(user_email, 'resume_json'))
        html = render_html(resume_dict=resume_dict, template_file=theme)

        # Create or update GitHub repo
        url = create_github_repo(
            repo_name,
            html,
            is_deployed
        )

        # Update user data
        update_this_column(user_email, "UI_ENDPOINT", url)
        update_this_column(user_email, "THEME", theme)

        return {
            "status_code": 200,
            "message": "Portfolio deployed successfully",
            "url": url
        }

    except HTTPException as http_exc:
            # logging.info(http_exc)
        raise http_exc
    except Exception as e:
        # Log unexpected exceptions and return 500
        logging.error(f"Deployment error for user {deploy_data.user_email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during deployment. Please try again."
        )


# ======================================== JOBS ===================================================================

@app.get("/all-jobs-api/")
def get_all_jobs_from_sf():

    conn = sf_client()
    try:
        cursor = conn.cursor()

        query = """
        SELECT POSTED_DATE, JOB_ROLE, TITLE, COMPANY, SENIORITY_LEVEL, EMPLOYMENT_TYPE, SKILLS, URL
        FROM JOB_HISTORY
        WHERE POSTED_DATE >= DATEADD(hour, -5, CURRENT_TIMESTAMP())
        ORDER BY POSTED_DATE DESC
        """
        cursor.execute(query)
        results = cursor.fetchall()
        column_names = ["POSTED_DATE", "JOB_ROLE", "TITLE", "COMPANY", "SENIORITY_LEVEL", "EMPLOYMENT_TYPE", "SKILLS", "URL"]
        df = pd.DataFrame(results, columns=column_names)
        data_dict = df.to_dict(orient="records") 
        return {"status_code": 200, "data":data_dict}
    except Exception as e:
        logging.info(f"Error fetching jobs from Snowflake: {str(e)}")
        logging.info(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error fetching jobs from Snowflake: {str(e)}")
    finally:
        conn.close()



@app.post("/jobs-api")
async def jobs_api(request: JobsRequest):
    """Consolidated endpoint for all job-related operations"""
    
    if request.filter is None:
        request.filter = JobFilter()
    action = request.filter.action or "filter"
    
    cache_needs_refresh = (
        JOBS_CACHE["data"] is None or
        JOBS_CACHE["timestamp"] is None or
        (datetime.now() - JOBS_CACHE["timestamp"]).seconds > 1800
    )
    if action == "status":
        return {
            "cache_exists": JOBS_CACHE["data"] is not None,
            "last_refresh": JOBS_CACHE["timestamp"].isoformat() if JOBS_CACHE["timestamp"] else None,
            "job_count": len(JOBS_CACHE["data"]) if JOBS_CACHE["data"] is not None else 0,
            "cache_age_seconds": (datetime.now() - JOBS_CACHE["timestamp"]).seconds if JOBS_CACHE["timestamp"] else None
        }
    elif action == "refresh":
        try:
            refresh_jobs_cache()
            return {"status": "success", "message": "Cache refreshed successfully"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error refreshing cache: {str(e)}")
    
    elif action == "interview-prep":
        if not request.interview_prep:
            raise HTTPException(status_code=400, detail="Interview prep data required for 'interview-prep' action")
        
        try:
            
            job_role = request.interview_prep.job_role
            skills = request.interview_prep.skills
            job_url = request.interview_prep.job_url
            
            return {
                "status": "success", 
                "message": f"Interview preparation materials for {job_role} role with focus on {', '.join(skills)} will be available soon!"
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing interview prep request: {str(e)}")
    
    elif action == "export":
        if cache_needs_refresh:
            try:
                refresh_jobs_cache()
            except Exception as e:
                if JOBS_CACHE["data"] is None:
                    raise HTTPException(status_code=500, detail=f"Error exporting jobs: {str(e)}")
        try:
            
            filtered_df = filter_jobs(
                JOBS_CACHE["data"],
                role=request.filter.role,
                time_filter=request.filter.time_filter,
                seniority_level=request.filter.seniority_level,
                employment_type=request.filter.employment_type
            )

            csv_str = filtered_df.to_csv(index=False)
            
            return {"csv_data": csv_str}
        
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error exporting jobs: {str(e)}")
    else:  
        if cache_needs_refresh:
            try:
                refresh_jobs_cache()
            except Exception as e:
                
                if JOBS_CACHE["data"] is None:
                    raise HTTPException(status_code=500, detail=f"Error fetching jobs: {str(e)}")
        try:
            
            filtered_df = filter_jobs(
                JOBS_CACHE["data"],
                role=request.filter.role,
                time_filter=request.filter.time_filter,
                seniority_level=request.filter.seniority_level,
                employment_type=request.filter.employment_type
            )
            
            jobs_list = filtered_df.to_dict(orient="records")
            
            for job in jobs_list:
                if isinstance(job["POSTED_DATE"], pd.Timestamp) or isinstance(job["POSTED_DATE"], datetime):
                    job["POSTED_DATE"] = job["POSTED_DATE"].isoformat()
            
            return {"jobs": jobs_list}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error retrieving jobs: {str(e)}")
