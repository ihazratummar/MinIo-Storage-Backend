from pydantic import BaseModel, Field, BeforeValidator
from typing import Optional, Annotated
from datetime import datetime

# Helper for ObjectId
PyObjectId = Annotated[str, BeforeValidator(str)]

class File(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    project_id: str
    bucket_name: str # Logical name
    object_key: str
    size: int
    content_type: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
