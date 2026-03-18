from rest_framework.views import APIView
from rest_framework.response import Response
from .models import BackgroundJob

from rest_framework import status

class GetJobStatus(APIView):
    permission_classes = []
    authentication_classes = []

    def get(self, request):
        job_id = request.GET.get("job_id")

        if not job_id:
            return Response({"error": "job_id required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            job = BackgroundJob.objects.get(id=job_id)
        except BackgroundJob.DoesNotExist:
            return Response({"error": "Job not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "status": job.status,
            "task_id": job.task_id
        })