import boto3
import os
import json

class BucketLoader:
    def __init__(self):
        self.s3=boto3.client("s3", endpoint_url=os.getenv("R2_ENDPOINT_URL"),
                aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
                region_name="auto")
        self.bucket=os.getenv("R2_BUCKET_NAME")

    def list_files(self):
        paginator = self.s3.get_paginator('list_objects_v2')

        for page in paginator.paginate(Bucket=self.bucket, Prefix="raw/"):
            contents=page.get('Contents', [])
            for obj in contents:
                yield obj

    def get_documents(self,obj):
        key=obj['Key']
        response=self.s3.get_object(Bucket=self.bucket,Key=key)
        raw=response['Body'].read()

        try:
            data=json.loads(raw)
            return{
                "text": data.get("texto",""),
                "metadata": {
                    "url": data.get("url",""),
                    "title": data.get("titulo",""),
                    **data.get("metadatos",{}),
                    "bucket_key": key
                }
            }
        except Exception as e:
            print(f"Error leyendo {key}: {e}")
            return None