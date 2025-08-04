import asyncio
import logging
from datetime import datetime
from typing import Optional
from celery import Task
from celery.exceptions import Retry
from tortoise import Tortoise
from app.tasks.celery_app import celery_app
from app.models.job import Job, JobStatus
from app.services.replicate_service import replicate_service
from app.services.storage_service import storage_service
from app.core.config import settings
from app.core.database import TORTOISE_ORM

logger = logging.getLogger(__name__)


class CallbackTask(Task):
    def on_success(self, retval, task_id, args, kwargs):
        logger.info(f"Task {task_id} succeeded")
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"Task {task_id} failed: {exc}")


@celery_app.task(bind=True, base=CallbackTask, autoretry_for=(Exception,))
def generate_media_task(self, job_id: int) -> dict:
    async def _generate_media():
        await Tortoise.init(config=TORTOISE_ORM)
        
        try:
            job = await Job.get(id=job_id)
            await job.update_from_dict({
                "status": JobStatus.PROCESSING,
                "started_at": datetime.utcnow()
            })
            await job.save()
            
            logger.info(f"Starting media generation for job {job_id}")
            
            media_urls = await replicate_service.generate_media(
                model=job.model,
                prompt=job.prompt,
                num_outputs=job.num_outputs,
                seed=job.seed,
                output_format=job.output_format
            )
            
            if not media_urls:
                raise Exception("No media URLs returned from Replicate")
            
            s3_key = await storage_service.upload_from_url(media_urls[0], job_id)
            
            await job.update_from_dict({
                "status": JobStatus.COMPLETED,
                "media_url": media_urls[0],
                "s3_key": s3_key,
                "completed_at": datetime.utcnow()
            })
            await job.save()
            
            logger.info(f"Successfully completed media generation for job {job_id}")
            return {"status": "success", "s3_key": s3_key}
            
        except Exception as e:
            logger.error(f"Error in media generation for job {job_id}: {str(e)}")
            
            try:
                job = await Job.get(id=job_id)
                current_retry = job.retry_count + 1
                
                backoff_delay = min(
                    settings.initial_retry_delay * (2 ** current_retry),
                    settings.max_retry_delay
                )
                
                if backoff_delay >= settings.max_retry_delay:
                    await job.update_from_dict({
                        "status": JobStatus.FAILED,
                        "error_message": str(e),
                        "retry_count": current_retry
                    })
                    await job.save()
                    raise e
                else:
                    await job.update_from_dict({
                        "status": JobStatus.RETRY,
                        "error_message": str(e),
                        "retry_count": current_retry
                    })
                    await job.save()
                    
                    raise self.retry(countdown=backoff_delay, max_retries=10)
                    
            except Exception as update_error:
                logger.error(f"Failed to update job status: {str(update_error)}")
                raise e
                
        finally:
            await Tortoise.close_connections()
    
    return asyncio.run(_generate_media())