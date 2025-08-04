from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.job import JobStatus


class JobCreateRequest(BaseModel):
    model: str = Field(..., description="Name of the model to use")
    prompt: str = Field(..., description="Text prompt for generation")
    num_outputs: int = Field(default=1, ge=1, le=10, description="Number of outputs to generate")
    seed: Optional[int] = Field(default=None, description="Seed for reproducibility")
    output_format: Optional[str] = Field(default=None, description="Output format (jpg, png, wav, mp3, etc.)")


class JobCreateResponse(BaseModel):
    job_id: int
    status: JobStatus
    message: str


class JobStatusResponse(BaseModel):
    job_id: int
    status: JobStatus
    model: str
    prompt: str
    num_outputs: int
    seed: Optional[int]
    output_format: Optional[str]
    media: Optional[List[dict]]
    error_message: Optional[str]
    retry_count: int
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None