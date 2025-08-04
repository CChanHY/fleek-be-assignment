from tortoise.models import Model
from tortoise import fields
from enum import Enum
from typing import Optional
from datetime import datetime


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"


class Job(Model):
    id = fields.IntField(pk=True)
    celery_task_id = fields.CharField(max_length=255, unique=True)
    
    model = fields.CharField(max_length=255)
    prompt = fields.TextField()
    num_outputs = fields.IntField(default=1)
    seed = fields.IntField(null=True)
    output_format = fields.CharField(max_length=50, null=True)
    
    status = fields.CharEnumField(JobStatus, default=JobStatus.PENDING)
    media = fields.JSONField(null=True)
    error_message = fields.TextField(null=True)
    retry_count = fields.IntField(default=0)
    
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    started_at = fields.DatetimeField(null=True)
    completed_at = fields.DatetimeField(null=True)
    
    class Meta:
        table = "jobs"
        
    def __str__(self):
        return f"Job {self.id} - {self.status}"