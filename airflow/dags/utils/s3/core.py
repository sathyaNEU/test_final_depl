import os
import boto3

def get_s3_client():
    try:
        s3_client = boto3.client(
        's3', 
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"), 
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION")  
        )
        return s3_client
    except:
        return -1
    
def write_markdown_to_s3(s3_client, md, path):    
    bucket_name, aws_region = os.getenv("BUCKET_NAME"), os.getenv('AWS_REGION')
    if bucket_name is None or aws_region is None:
        return -1
    try:
        s3_client.put_object(Bucket=bucket_name, Key=path, Body=md.encode('utf-8'), ContentType='text/markdown')
        object_url = f"https://{bucket_name}.s3.{aws_region}.amazonaws.com/{path}"
        return object_url
    except Exception as e:
        print(e)
        return -1 