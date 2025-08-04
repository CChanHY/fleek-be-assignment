import boto3
import httpx
import logging
from typing import Optional
from uuid import uuid4
from botocore.exceptions import ClientError
from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
            region_name=settings.s3_region_name
        )
        self.bucket_name = settings.s3_bucket_name
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                try:
                    self.s3_client.create_bucket(Bucket=self.bucket_name)
                    logger.info(f"Created bucket: {self.bucket_name}")
                except ClientError as create_error:
                    logger.error(f"Failed to create bucket: {create_error}")
                    raise create_error
            else:
                logger.error(f"Error checking bucket: {e}")
                raise e
    
    async def upload_from_url(self, media_url: str, job_id: int) -> str:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(media_url)
                response.raise_for_status()
                
                file_extension = self._get_file_extension_from_url(media_url)
                s3_key = f"jobs/{job_id}/{uuid4()}{file_extension}"
                
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Body=response.content,
                    ContentType=response.headers.get('content-type', 'application/octet-stream')
                )
                
                logger.info(f"Successfully uploaded media with key: {s3_key}")
                return s3_key
                
        except Exception as e:
            logger.error(f"Error uploading media from URL {media_url}: {str(e)}")
            raise e
    
    def _get_file_extension_from_url(self, url: str) -> str:
        if url.lower().endswith('.jpg') or url.lower().endswith('.jpeg'):
            return '.jpg'
        elif url.lower().endswith('.png'):
            return '.png'
        elif url.lower().endswith('.gif'):
            return '.gif'
        elif url.lower().endswith('.mp4'):
            return '.mp4'
        elif url.lower().endswith('.wav'):
            return '.wav'
        elif url.lower().endswith('.mp3'):
            return '.mp3'
        else:
            return '.bin'
    
    def get_presigned_url(self, s3_key: str, expiration: int = 3600) -> str:
        try:
            response = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expiration
            )
            return response
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {e}")
            raise e


storage_service = StorageService()