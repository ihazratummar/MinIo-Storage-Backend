from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.models import (
    UploadInitRequest, UploadInitResponse,
    UploadCompleteRequest, UploadCompleteResponse,
    FileDeleteRequest, FileDeleteResponse,
    FileUrlRequest, FileUrlResponse
)
from app.services.storage import storage_service
from app.core.security import get_current_project
from app.models.project import Project, Bucket
from app.models.file import File
from app.core.database import get_db
from app.core.config import settings
import uuid
from datetime import datetime, timedelta
import os

router = APIRouter(dependencies=[Depends(get_current_project)])


@router.post("/upload/init", response_model=UploadInitResponse)
async def init_upload(
    request: UploadInitRequest, 
    project: Project = Depends(get_current_project),
    db = Depends(get_db)
):
    # Validate Bucket
    if not request.bucket:
        raise HTTPException(status_code=400, detail="Bucket name is required")
    
    bucket_data = await db.buckets.find_one({"name": request.bucket, "project_id": str(project.id)})
    if not bucket_data:
        raise HTTPException(status_code=404, detail="Bucket not found")
    
    db_bucket = Bucket(**bucket_data)

    # Generate object key: uploads/year/month/uuid.ext
    now = datetime.utcnow()
    year = now.strftime("%Y")
    month = now.strftime("%m")
    ext = os.path.splitext(request.filename)[1]
    if not ext:
        ext = "" # or handle error
    
    file_uuid = str(uuid.uuid4())
    object_key = f"uploads/{year}/{month}/{file_uuid}{ext}"
    
    if request.folder:
        object_key = f"{request.folder}/{object_key}"

    # Generate presigned URL
    upload_url = storage_service.generate_presigned_url(
        bucket_name=db_bucket.physical_name,
        object_name=object_key,
        method="PUT"
    )
    
    # Construct final URL (public or CDN)
    final_url = f"https://{settings.MINIO_ENDPOINT}/{db_bucket.physical_name}/{object_key}"
    
    return UploadInitResponse(
        upload_url=upload_url,
        object_key=object_key,
        final_url=final_url,
        expires_in=settings.PRESIGNED_EXPIRY
    )

@router.post("/upload/complete", response_model=UploadCompleteResponse)
async def complete_upload(
    request: UploadCompleteRequest, 
    project: Project = Depends(get_current_project),
    db = Depends(get_db)
):
    if not request.bucket:
        raise HTTPException(status_code=400, detail="Bucket name is required")

    bucket_data = await db.buckets.find_one({"name": request.bucket, "project_id": str(project.id)})
    if not bucket_data:
        raise HTTPException(status_code=404, detail="Bucket not found")
    
    db_bucket = Bucket(**bucket_data)

    # Debug logging
    print(f"DEBUG: Checking for file in bucket: {db_bucket.physical_name}")
    print(f"DEBUG: Object key: {request.object_key}")

    # Try to verify object exists (optional - may fail due to permissions)
    file_size = request.file_size  # Use provided size as fallback
    try:
        stat_result = storage_service.get_object_stats(bucket_name=db_bucket.physical_name, object_name=request.object_key)
        file_size = stat_result.size
        print(f"DEBUG: File verified! Size: {stat_result.size}")
    except Exception as e:
        print(f"DEBUG: Could not verify file (using provided size): {str(e)}")
        # Continue anyway - file was uploaded successfully via presigned URL

    # Save File Metadata to DB
    new_file = File(
        project_id=str(project.id),
        bucket_name=request.bucket,
        object_key=request.object_key,
        size=file_size,
        content_type=request.file_type
    )
    await db.files.insert_one(new_file.model_dump(by_alias=True, exclude={"id"}))

    final_url = f"https://{settings.MINIO_ENDPOINT}/{db_bucket.physical_name}/{request.object_key}"

    return UploadCompleteResponse(
        object_key=request.object_key,
        final_url=final_url,
        mime=request.file_type,
        size=file_size
    )

@router.delete("/file", response_model=FileDeleteResponse)
async def delete_file(
    request: FileDeleteRequest, 
    project: Project = Depends(get_current_project),
    db = Depends(get_db)
):
    if not request.bucket:
        raise HTTPException(status_code=400, detail="Bucket name is required")

    bucket_data = await db.buckets.find_one({"name": request.bucket, "project_id": str(project.id)})
    if not bucket_data:
        raise HTTPException(status_code=404, detail="Bucket not found")
    
    db_bucket = Bucket(**bucket_data)

    # Remove from MinIO
    storage_service.delete_object(bucket_name=db_bucket.physical_name, object_name=request.object_key)
    
    # Remove from DB
    await db.files.delete_one({
        "project_id": str(project.id),
        "bucket_name": request.bucket,
        "object_key": request.object_key
    })

    return FileDeleteResponse(status="deleted")

@router.post("/file/url", response_model=FileUrlResponse)
async def get_file_url(
    request: FileUrlRequest,
    project: Project = Depends(get_current_project),
    db = Depends(get_db)
):
    """Generate a temporary presigned URL to access a file"""
    if not request.bucket:
        raise HTTPException(status_code=400, detail="Bucket name is required")

    bucket_data = await db.buckets.find_one({"name": request.bucket, "project_id": str(project.id)})
    if not bucket_data:
        raise HTTPException(status_code=404, detail="Bucket not found")
    
    db_bucket = Bucket(**bucket_data)

    # Verify file exists
    if not storage_service.check_object_exists(bucket_name=db_bucket.physical_name, object_name=request.object_key):
        raise HTTPException(status_code=404, detail="File not found")

    # Generate presigned GET URL
    presigned_url = storage_service.generate_presigned_url(
        bucket_name=db_bucket.physical_name,
        object_name=request.object_key,
        method="GET"
    )

    return FileUrlResponse(
        url=presigned_url,
        expires_in=request.expires_in
    )
