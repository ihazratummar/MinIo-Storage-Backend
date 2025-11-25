from pydantic import BaseModel
from typing import Optional

class UploadInitRequest(BaseModel):
    filename: str
    file_type: str
    file_size: int
    folder: Optional[str] = None
    bucket: str

class UploadInitResponse(BaseModel):
    upload_url: str
    object_key: str
    final_url: str
    expires_in: int

class UploadCompleteRequest(BaseModel):
    object_key: str
    file_size: int
    file_type: str
    bucket: str

class UploadCompleteResponse(BaseModel):
    object_key: str
    final_url: str
    mime: str
    size: int

class FileDeleteRequest(BaseModel):
    object_key: str
    bucket: str

class FileDeleteResponse(BaseModel):
    status: str

class FileUrlRequest(BaseModel):
    object_key: str
    bucket: str
    expires_in: Optional[int] = 3600  # 1 hour default

class FileUrlResponse(BaseModel):
    url: str
    expires_in: int
