from django.db import models
import uuid
from django.utils import timezone

class BackgroundJob(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    task_type = models.CharField(max_length=100)
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.PENDING,
        db_index=True
    )
    
    # Generic relation to related objects (simplified)
    related_object_type = models.CharField(max_length=100)
    related_object_id = models.BigIntegerField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['related_object_type', 'related_object_id']),
        ]

    def mark_processing(self, task_id=None):
        self.status = self.Status.PROCESSING
        self.started_at = timezone.now()
        self.finished_at = None
        self.error = None
        if task_id:
            self.task_id = task_id
        self.save(update_fields=['status', 'started_at', 'task_id', 'finished_at', 'error'])

    def mark_completed(self):
        self.status = self.Status.COMPLETED
        self.finished_at = timezone.now()
        self.error = None
        self.save(update_fields=['status', 'finished_at', 'error'])

    def mark_failed(self, error_message):
        self.status = self.Status.FAILED
        self.finished_at = timezone.now()
        self.error = error_message
        self.save(update_fields=['status', 'finished_at', 'error'])

    def __str__(self):
        return f"{self.task_type} - {self.status} ({self.id})"
