import logging
from celery import shared_task
from django.utils import timezone
from .models import BackgroundJob

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def example_tracked_task(self, job_id, *args, **kwargs):
    """
    Example Celery task that demonstrates background job lifecycle tracking.
    """
    try:
        # Retrieve the job record
        try:
            job = BackgroundJob.objects.get(id=job_id)
        except BackgroundJob.DoesNotExist:
            logger.error(f"BackgroundJob {job_id} not found.")
            return

        # 1. Mark as Processing
        job.mark_processing(task_id=self.request.id)
        logger.info(f"Started processing job {job_id}")

        # --- Simulate Work ---
        # Replace this with actual business logic
        import time
        time.sleep(5) 
        
        # Example of handling a specific logic-driven failure
        if kwargs.get('fail_simulated'):
            raise ValueError("Simulated task failure")
        # ---------------------

        # 2. Mark as Completed
        job.mark_completed()
        logger.info(f"Successfully completed job {job_id}")
        return f"Job {job_id} completed"

    except Exception as exc:
        # 3. Mark as Failed
        error_msg = f"{type(exc).__name__}: {str(exc)}"
        try:
            job = BackgroundJob.objects.get(id=job_id)
            job.mark_failed(error_msg)
        except Exception:
            logger.error(f"Could not update job {job_id} status to failed: {error_msg}")

        logger.error(f"Error in example_tracked_task: {error_msg}")
        
        # Optionally retry for transient failures
        if isinstance(exc, (ConnectionError, TimeoutError)):
             raise self.retry(exc=exc, countdown=60)
             
        raise exc
