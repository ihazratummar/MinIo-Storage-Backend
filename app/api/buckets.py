from fastapi import APIRouter, Depends, HTTPException
from app.core.database import get_db
from app.models.project import Project, Bucket, BucketCreate, BucketRead
from app.core.security import get_current_project
from app.services.storage import storage_service
import uuid

router = APIRouter()

@router.post("/buckets", response_model=BucketRead)
async def create_bucket(
    bucket: BucketCreate, 
    project: Project = Depends(get_current_project),
    db = Depends(get_db)
):
    # Check if bucket name exists for this project
    existing = await db.buckets.find_one({"name": bucket.name, "project_id": str(project.id)})
    if existing:
        raise HTTPException(status_code=400, detail="Bucket name already exists for this project")

    # Generate physical name: project_id-bucket_name-uuid
    physical_name = f"{str(project.id)}-{bucket.name.lower()}-{str(uuid.uuid4())[:8]}"

    # Create Bucket in MinIO
    try:
        if not storage_service.client.bucket_exists(bucket_name=physical_name):
             storage_service.client.make_bucket(bucket_name=physical_name)
             
             # Set public-read policy for permanent access
             import json
             policy = {
                 "Version": "2012-10-17",
                 "Statement": [
                     {
                         "Effect": "Allow",
                         "Principal": {"AWS": "*"},
                         "Action": ["s3:GetObject"],
                         "Resource": [f"arn:aws:s3:::{physical_name}/*"]
                     }
                 ]
             }
             storage_service.client.set_bucket_policy(bucket_name=physical_name, policy=json.dumps(policy))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create bucket in storage: {str(e)}")

    # Save to DB
    new_bucket = Bucket(
        name=bucket.name,
        physical_name=physical_name,
        project_id=str(project.id)
    )
    
    result = await db.buckets.insert_one(new_bucket.model_dump(by_alias=True, exclude={"id"}))
    created_bucket = await db.buckets.find_one({"_id": result.inserted_id})
    
    return created_bucket

@router.get("/buckets", response_model=list[BucketRead])
async def list_buckets(
    project: Project = Depends(get_current_project),
    db = Depends(get_db)
):
    buckets = await db.buckets.find({"project_id": str(project.id)}).to_list(1000)
    return buckets

@router.delete("/buckets/{name}")
async def delete_bucket(
    name: str,
    project: Project = Depends(get_current_project),
    db = Depends(get_db)
):
    # Find bucket
    bucket_data = await db.buckets.find_one({"name": name, "project_id": str(project.id)})
    if not bucket_data:
        raise HTTPException(status_code=404, detail="Bucket not found")
    
    db_bucket = Bucket(**bucket_data)

    # Try to remove from MinIO (will fail if not empty)
    try:
        storage_service.client.remove_bucket(bucket_name=db_bucket.physical_name)
    except Exception as e:
        # Check if error is "BucketNotEmpty"
        if "BucketNotEmpty" in str(e):
             raise HTTPException(status_code=400, detail="Bucket is not empty. Please delete all files first.")
        raise HTTPException(status_code=500, detail=f"Failed to delete bucket in storage: {str(e)}")

    # Remove from DB
    await db.buckets.delete_one({"_id": bucket_data["_id"]})
    return {"status": "deleted", "name": name}

@router.put("/buckets/{name}", response_model=BucketRead)
async def update_bucket(
    name: str,
    bucket_update: BucketCreate,
    project: Project = Depends(get_current_project),
    db = Depends(get_db)
):
    # Find bucket
    bucket_data = await db.buckets.find_one({"name": name, "project_id": str(project.id)})
    if not bucket_data:
        raise HTTPException(status_code=404, detail="Bucket not found")

    # Check if new name exists
    if bucket_update.name != name:
        existing = await db.buckets.find_one({"name": bucket_update.name, "project_id": str(project.id)})
        if existing:
            raise HTTPException(status_code=400, detail="Bucket name already exists")

    # Update logical name only
    await db.buckets.update_one(
        {"_id": bucket_data["_id"]},
        {"$set": {"name": bucket_update.name}}
    )
    
    updated_bucket = await db.buckets.find_one({"_id": bucket_data["_id"]})
    return updated_bucket
