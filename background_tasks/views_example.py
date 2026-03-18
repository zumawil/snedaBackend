from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import BackgroundJob
from .tasks import example_tracked_task

class ExampleTaskTriggerView(APIView):
    """
    Example API view demonstrating how to safely initialize a background job
    and queue the Celery task using transaction.on_commit.
    """
    def post(self, request):
        related_id = request.data.get('order_id', 1) # Example related object
        
        # 1. Create the tracking record in 'pending' state
        job = BackgroundJob.objects.create(
            task_type="example_work",
            related_object_type="order",
            related_object_id=related_id
        )

        # 2. Queue the Celery task safely
        # We use transaction.on_commit to ensure the task is only queued 
        # AFTER the database transaction is successfully committed.
        def dispatch_task():
            result = example_tracked_task.delay(job_id=job.id)
            # Capture the Celery task_id immediately
            job.task_id = result.id
            job.save(update_fields=['task_id'])

        transaction.on_commit(dispatch_task)

        return Response({
            "success": True,
            "message": "Task queued successfully",
            "job_id": str(job.id),
            "status": job.status
        }, status=status.HTTP_202_ACCEPTED)
