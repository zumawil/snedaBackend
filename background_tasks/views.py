from rest_framework.views import APIView
from rest_framework.response import Response
from .models import BackgroundJob

from rest_framework import status
import uuid

def is_valid_uuid(val : str) -> bool:
    try:
        uuid_obj = uuid.UUID(val)
        return str(uuid_obj) == val.lower()
    except ValueError:
        return False

class GetJobStatus(APIView):
    permission_classes = []
    authentication_classes = []

    def get(self, request):
        job_id = request.GET.get("job_id")

        if not job_id:
            return Response({"error": "job_id required"}, status=status.HTTP_400_BAD_REQUEST)

        if not is_valid_uuid(job_id):
            return Response({"error": "Invalid job_id"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            job = BackgroundJob.objects.get(id=job_id, user=request.user)
        except BackgroundJob.DoesNotExist:
            return Response({"error": "Job not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "status": job.status,
            "task_id": job.task_id
        })