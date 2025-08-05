from fastapi import APIRouter, HTTPException, status
from app.schemas.job import JobCreateRequest, JobCreateResponse, JobStatusResponse, ErrorResponse
from app.models.job import Job, JobStatus
from app.tasks.media_generation import start_media_generation_workflow
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
        
        task = start_media_generation_workflow(job.id)
        
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
        
        media = []
        
        # Query child jobs (persist_media_to_s3 tasks)
        child_jobs = await Job.filter(parent_id=job_id).all()
        
        if child_jobs:
            # Use child jobs to build media array with status information
            for child_job in child_jobs:
                # Get media_url from the media field
                media_url = None
                if child_job.media and isinstance(child_job.media, list) and len(child_job.media) > 0:
                    media_url = child_job.media[0].get('media_url')
                
                media_item = {
                    'media_url': media_url,
                    'status': child_job.status,
                    'error_message': child_job.error_message,
                    'started_at': child_job.started_at,
                    'completed_at': child_job.completed_at
                }
                
                # Add S3 info and presigned URL if available
                if child_job.media and isinstance(child_job.media, list) and len(child_job.media) > 0:
                    s3_key = child_job.media[0].get('s3_key')
                    if s3_key:
                        media_item['s3_key'] = s3_key
                        try:
                            presigned_url = storage_service.get_presigned_url(s3_key)
                            media_item['presigned_media_url'] = presigned_url
                        except Exception as e:
                            logger.error(f"Error generating presigned URL for child job {child_job.id}: {str(e)}")
                            media_item['presigned_media_url'] = None
                
                media.append(media_item)
        else:
            # Fallback to original media field if no child jobs exist
            if job.media and isinstance(job.media, list):
                for media_item in job.media:
                    try:
                        presigned_url = storage_service.get_presigned_url(media_item['s3_key'])
                        media.append({
                            'media_url': media_item['media_url'],
                            'presigned_media_url': presigned_url
                        })
                    except Exception as e:
                        logger.error(f"Error generating presigned URL for job {job_id}: {str(e)}")
                        media.append({
                            'media_url': media_item.get('media_url'),
                            'presigned_media_url': None
                        })
        
        return JobStatusResponse(
            job_id=job.id,
            status=job.status,
            model=job.model,
            prompt=job.prompt,
            num_outputs=job.num_outputs,
            seed=job.seed,
            output_format=job.output_format,
            media=media,
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