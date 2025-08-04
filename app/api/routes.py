from fastapi import APIRouter, HTTPException, status
from app.schemas.job import JobCreateRequest, JobCreateResponse, JobStatusResponse, ErrorResponse
from app.models.job import Job, JobStatus
from app.tasks.media_generation import generate_media_task
from app.services.storage_service import storage_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/generate", response_model=JobCreateResponse)
async def create_generation_job(request: JobCreateRequest):
    try:
        job = await Job.create(
            model=request.model,
            prompt=request.prompt,
            num_outputs=request.num_outputs,
            seed=request.seed,
            output_format=request.output_format,
            celery_task_id="temp"  # Will be updated after task creation
        )
        
        task = generate_media_task.delay(job.id)
        
        job.celery_task_id = task.id
        await job.save()
        
        logger.info(f"Created job {job.id} with task {task.id}")
        
        return JobCreateResponse(
            job_id=job.id,
            status=job.status,
            message="Job created and queued for processing"
        )
        
    except Exception as e:
        logger.error(f"Error creating generation job: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create job: {str(e)}"
        )


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: int):
    try:
        job = await Job.get_or_none(id=job_id)
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )
        
        presigned_media_url = None
        s3_key = job.s3_key
        
        # Handle legacy jobs where s3_key is null but media_url contains S3 URL
        if not s3_key and job.media_url and job.media_url.startswith(f"http"):
            try:
                # Extract S3 key from URL like: http://minio:9000/media-generation/jobs/1/file.jpg
                # Should extract: jobs/1/file.jpg
                url_parts = job.media_url.split("/")
                if len(url_parts) >= 3:
                    s3_key = "/".join(url_parts[-3:])  # Get last 3 parts: jobs/1/filename
            except Exception as e:
                logger.error(f"Error extracting S3 key from media_url for job {job_id}: {str(e)}")
        
        if s3_key:
            try:
                presigned_media_url = storage_service.get_presigned_url(s3_key)
            except Exception as e:
                logger.error(f"Error generating presigned URL for job {job_id}: {str(e)}")
        
        return JobStatusResponse(
            job_id=job.id,
            status=job.status,
            model=job.model,
            prompt=job.prompt,
            num_outputs=job.num_outputs,
            seed=job.seed,
            output_format=job.output_format,
            media_url=job.media_url,
            presigned_media_url=presigned_media_url,
            error_message=job.error_message,
            retry_count=job.retry_count,
            created_at=job.created_at,
            updated_at=job.updated_at,
            started_at=job.started_at,
            completed_at=job.completed_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status for {job_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job status: {str(e)}"
        )