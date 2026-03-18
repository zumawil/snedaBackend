from django.urls import path
from .views import GetJobStatus

urlpatterns = [
    path('get-job-status/', GetJobStatus.as_view(), name='get-job-status'),
]