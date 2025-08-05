import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Dict
from celery import Task, chord, group, chain
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


@celery_app.task(bind=True, base=CallbackTask)
def persist_media_to_s3(self, media_url: str, job_id: int, child_job_id: int) -> Dict:
    """Upload a single media file to S3."""
    async def _upload_media():
        await Tortoise.init(config=TORTOISE_ORM)
        try:
            # Update child job status to processing and set celery_task_id
            child_job = await Job.get(id=child_job_id)
            await child_job.update_from_dict({
                "celery_task_id": self.request.id,
                "status": JobStatus.PROCESSING,
                "started_at": datetime.utcnow()
            })
            await child_job.save()
            
            s3_key = await storage_service.upload_from_url(media_url, job_id)
            logger.info(f"Successfully uploaded media {media_url} to S3 with key: {s3_key}")
            
            # Update child job with completion status and results
            await child_job.update_from_dict({
                "status": JobStatus.COMPLETED,
                "media": [{
                    "media_url": media_url,
                    "s3_key": s3_key
                }],
                "completed_at": datetime.utcnow()
            })
            await child_job.save()
            
            return {
                "media_url": media_url,
                "s3_key": s3_key,
                "child_job_id": child_job_id
            }
        except Exception as e:
            # Update child job with failure status
            try:
                child_job = await Job.get(id=child_job_id)
                await child_job.update_from_dict({
                    "status": JobStatus.FAILED,
                    "error_message": str(e),
                    "completed_at": datetime.utcnow()
                })
                await child_job.save()
            except Exception as update_error:
                logger.error(f"Failed to update child job {child_job_id} status: {str(update_error)}")
            raise e
        finally:
            await Tortoise.close_connections()
    
    return asyncio.run(_upload_media())


@celery_app.task(bind=True, base=CallbackTask)
def trigger_media_persistence_chord(self, media_urls: List[str], job_id: int, child_job_ids: List[int]):
    """Trigger parallel media uploads using a dynamic chord."""
    logger.info(f"Triggering chord for {len(media_urls)} media files for job {job_id}")
    
    # Create parallel upload tasks with corresponding child job IDs
    upload_tasks = [persist_media_to_s3.s(media_url, job_id, child_job_id) 
                   for media_url, child_job_id in zip(media_urls, child_job_ids)]
    
    # Create chord with callback
    job_result = chord(upload_tasks)(finalize_media_generation.s(job_id))
    return {"chord_id": job_result.id, "job_id": job_id}


@celery_app.task(bind=True, base=CallbackTask)
def finalize_media_generation(self, media_results: List[Dict], job_id: int) -> Dict:
    """Finalize job after all media files have been uploaded."""
    async def _finalize():
        await Tortoise.init(config=TORTOISE_ORM)
        try:
            job = await Job.get(id=job_id)
            await job.update_from_dict({
                "status": JobStatus.COMPLETED,
                "media": media_results,
                "completed_at": datetime.utcnow()
            })
            await job.save()
            
            logger.info(f"Successfully completed media generation for job {job_id} with {len(media_results)} media files")
            return {"status": "success", "media": media_results}
        except Exception as e:
            logger.error(f"Error finalizing job {job_id}: {str(e)}")
            try:
                job = await Job.get(id=job_id)
                await job.update_from_dict({
                    "status": JobStatus.FAILED,
                    "error_message": f"Failed to finalize: {str(e)}"
                })
                await job.save()
            except Exception as update_error:
                logger.error(f"Failed to update job status during finalization: {str(update_error)}")
            raise e
        finally:
            await Tortoise.close_connections()
    
    return asyncio.run(_finalize())


def start_media_generation_workflow(job_id: int):
    """Start the media generation workflow with dynamic chord for parallel uploads."""
    workflow = chain(
        generate_media_task.s(job_id),
        orchestrate_media_workflow.s()
    )
    return workflow.delay()


@celery_app.task(bind=True, base=CallbackTask)
def orchestrate_media_workflow(self, result: Dict) -> Dict:
    """Orchestrate the workflow after media generation is complete."""
    if result.get("status") == "media_generated":
        media_urls = result["media_urls"]
        job_id = result["job_id"]
        
        async def _create_child_jobs():
            await Tortoise.init(config=TORTOISE_ORM)
            try:
                child_job_ids = []
                for i, media_url in enumerate(media_urls):
                    child_job = await Job.create(
                        celery_task_id=f"{job_id}_upload_{i}_pending",
                        parent_id=job_id,
                        model="",
                        prompt="",
                        num_outputs=0,
                        media=[{"media_url": media_url}],
                        status=JobStatus.PENDING
                    )
                    child_job_ids.append(child_job.id)
                return child_job_ids
            finally:
                await Tortoise.close_connections()
        
        child_job_ids = asyncio.run(_create_child_jobs())
        
        # Trigger the chord for parallel uploads with child job IDs
        return trigger_media_persistence_chord.delay(media_urls, job_id, child_job_ids)
    else:
        # If media generation returned a different status, pass it through
        return result


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
            
            # Trigger parallel media persistence using chord
            logger.info(f"Media generation completed for job {job_id}. Triggering parallel uploads.")
            
            # Return media URLs to trigger the chord in a separate task
            return {"status": "media_generated", "media_urls": media_urls, "job_id": job_id}
            
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