from pydantic import BaseModel, Field, BeforeValidator
from typing import Optional, List, Annotated
from datetime import datetime

# Helper for ObjectId
PyObjectId = Annotated[str, BeforeValidator(str)]

class Project(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    name: str
    api_key: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "name": "My Project",
                "api_key": "secret_key"
            }
        }

class Bucket(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    name: str
    physical_name: str
    project_id: str # Store as string (ObjectId)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True

class ProjectCreate(BaseModel):
    name: str

class ProjectRead(Project):
    bucket_count: int = 0
    file_count: int = 0
    total_size: int = 0

class BucketCreate(BaseModel):
    name: str

class BucketRead(BaseModel):
    id: PyObjectId = Field(alias="_id")
    name: str
    physical_name: str
    created_at: datetime
