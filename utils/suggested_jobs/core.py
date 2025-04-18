from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import snowflake.connector
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
import traceback
import logging
from utils.snowflake.snowflake_connector import sf_client


JOBS_CACHE = {
        "data": None,
        "timestamp": None
    }
    

def get_all_jobs_from_snowflake():
    
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
        
        return df
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching jobs from Snowflake: {str(e)}")
    finally:
        conn.close()

def filter_jobs(jobs_df, role=None, time_filter=None, seniority_level=None, employment_type=None):
    """
    Filter jobs data locally (no Snowflake query)
    """
    if jobs_df is None or jobs_df.empty:
        return pd.DataFrame(columns=["POSTED_DATE", "JOB_ROLE", "TITLE", "COMPANY", "SENIORITY_LEVEL", "EMPLOYMENT_TYPE", "SKILLS", "URL"])
    
    
    filtered_df = jobs_df.copy()
    
    
    if role:
        filtered_df = filtered_df[filtered_df["JOB_ROLE"] == role]
    
    
    if time_filter:
        hours_map = {
            "30min": 0.5,
            "1hr": 1,
            "2hr": 2,
            "3hr": 3,
            "4hr": 4
        }
        
        if time_filter in hours_map:
            hours = hours_map[time_filter]
            cutoff_time = datetime.now() - timedelta(hours=hours)
            filtered_df = filtered_df[filtered_df["POSTED_DATE"] >= cutoff_time]
    
    if seniority_level and seniority_level != "All Levels":
        filtered_df = filtered_df[filtered_df["SENIORITY_LEVEL"].fillna("Not Applicable") == seniority_level]
    
    if employment_type and employment_type != "All Types":
        filtered_df = filtered_df[filtered_df["EMPLOYMENT_TYPE"].fillna("Not Applicable") == employment_type]
    
    return filtered_df

def refresh_jobs_cache():
    """Refresh the jobs cache from Snowflake"""
    try:
        JOBS_CACHE["data"] = get_all_jobs_from_snowflake()
        JOBS_CACHE["timestamp"] = datetime.now()
    except Exception as e:
        raise