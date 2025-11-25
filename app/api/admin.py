from fastapi import APIRouter, Depends, HTTPException
from app.core.database import get_db
from app.models.project import Project, ProjectCreate, ProjectRead
from app.core.security import verify_admin
import secrets

router = APIRouter(dependencies=[Depends(verify_admin)])

@router.post("/projects", response_model=ProjectRead)
async def create_project(project: ProjectCreate, db = Depends(get_db)):
    # Check if name exists
    existing = await db.projects.find_one({"name": project.name})
    if existing:
        raise HTTPException(status_code=400, detail="Project name already exists")

    # Generate API Key
    api_key = secrets.token_urlsafe(32)
    
    # Save to DB
    new_project = Project(
        name=project.name,
        api_key=api_key
    )
    
    try:
        dump = new_project.model_dump(by_alias=True, exclude={"id"})
        print(f"DEBUG: Inserting project: {dump}")
        result = await db.projects.insert_one(dump)
        print(f"DEBUG: Inserted ID: {result.inserted_id}")
        created_project = await db.projects.find_one({"_id": result.inserted_id})
        return created_project
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/projects", response_model=list[ProjectRead])
async def list_projects(db = Depends(get_db)):
    """Optimized project listing using aggregation pipeline"""
    
    # Single aggregation pipeline to get all data at once
    pipeline = [
        # Lookup buckets
        {
            "$lookup": {
                "from": "buckets",
                "let": {"project_id": {"$toString": "$_id"}},
                "pipeline": [
                    {"$match": {"$expr": {"$eq": ["$project_id", "$$project_id"]}}}
                ],
                "as": "buckets"
            }
        },
        # Lookup files
        {
            "$lookup": {
                "from": "files",
                "let": {"project_id": {"$toString": "$_id"}},
                "pipeline": [
                    {"$match": {"$expr": {"$eq": ["$project_id", "$$project_id"]}}},
                    {
                        "$group": {
                            "_id": None,
                            "count": {"$sum": 1},
                            "total_size": {"$sum": "$size"}
                        }
                    }
                ],
                "as": "file_stats"
            }
        },
        # Project final shape
        {
            "$project": {
                "_id": 1,
                "name": 1,
                "api_key": 1,
                "created_at": 1,
                "bucket_count": {"$size": "$buckets"},
                "file_count": {
                    "$ifNull": [{"$arrayElemAt": ["$file_stats.count", 0]}, 0]
                },
                "total_size": {
                    "$ifNull": [{"$arrayElemAt": ["$file_stats.total_size", 0]}, 0]
                }
            }
        }
    ]
    
    projects = await db.projects.aggregate(pipeline).to_list(1000)
    return projects

@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    db = Depends(get_db)
):
    """Delete a project and ALL associated data (buckets, files, MinIO buckets)"""
    from app.services.storage import storage_service
    from bson import ObjectId
    
    # Find project
    try:
        project_data = await db.projects.find_one({"_id": ObjectId(project_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid project ID")
    
    if not project_data:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project = Project(**project_data)
    
    # Get all buckets for this project
    buckets = await db.buckets.find({"project_id": project_id}).to_list(1000)
    
    # Delete all MinIO buckets and their contents
    for bucket_data in buckets:
        physical_name = bucket_data["physical_name"]
        try:
            # List and delete all objects in the bucket
            objects = storage_service.client.list_objects(physical_name, recursive=True)
            for obj in objects:
                storage_service.client.remove_object(physical_name, obj.object_name)
            
            # Delete the bucket itself
            storage_service.client.remove_bucket(physical_name)
        except Exception as e:
            print(f"Warning: Failed to delete MinIO bucket {physical_name}: {str(e)}")
    
    # Delete all files metadata from DB
    await db.files.delete_many({"project_id": project_id})
    
    # Delete all buckets from DB
    await db.buckets.delete_many({"project_id": project_id})
    
    # Delete the project itself
    await db.projects.delete_one({"_id": ObjectId(project_id)})
    
    return {
        "status": "deleted",
        "project_id": project_id,
        "project_name": project.name,
        "buckets_deleted": len(buckets)
    }

@router.put("/projects/{project_id}/regenerate-key")
async def regenerate_api_key(
    project_id: str,
    db = Depends(get_db)
):
    """Regenerate API key for a project (use when key is compromised)"""
    from bson import ObjectId
    
    # Find project
    try:
        project_data = await db.projects.find_one({"_id": ObjectId(project_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid project ID")
    
    if not project_data:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Generate new API key
    new_api_key = secrets.token_urlsafe(32)
    
    # Update in database
    await db.projects.update_one(
        {"_id": ObjectId(project_id)},
        {"$set": {"api_key": new_api_key}}
    )
    
    return {
        "status": "regenerated",
        "project_id": project_id,
        "new_api_key": new_api_key
    }

@router.post("/projects/{project_id}/sync")
async def sync_project(
    project_id: str,
    db = Depends(get_db)
):
    """Sync MongoDB state with actual MinIO storage"""
    from app.services.storage import storage_service
    from bson import ObjectId
    from app.models.file import File
    
    # Find project
    try:
        project_data = await db.projects.find_one({"_id": ObjectId(project_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid project ID")
    
    if not project_data:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get all buckets
    buckets = await db.buckets.find({"project_id": project_id}).to_list(1000)
    
    stats = {
        "added": 0,
        "removed": 0,
        "updated": 0,
        "errors": []
    }
    
    for bucket in buckets:
        physical_name = bucket["physical_name"]
        bucket_name = bucket["name"]
        
        try:
            # Check if bucket exists in MinIO
            if not storage_service.client.bucket_exists(bucket_name=physical_name):
                print(f"WARNING: Bucket {physical_name} missing in MinIO. Recreating...")
                storage_service.client.make_bucket(bucket_name=physical_name)
                # Set policy to public-read (optional, but good for consistency)
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
                minio_objects = []
            else:
                # Get all objects from MinIO
                minio_objects = storage_service.client.list_objects(bucket_name=physical_name, recursive=True)
            
            minio_map = {obj.object_name: obj for obj in minio_objects}
            
            # Get all files from DB
            db_files = await db.files.find({
                "project_id": project_id,
                "bucket_name": bucket_name
            }).to_list(10000)
            db_map = {f["object_key"]: f for f in db_files}
            
            # 1. Check for missing files (in MinIO but not DB)
            for obj_key, obj in minio_map.items():
                if obj_key not in db_map:
                    # Add to DB
                    new_file = File(
                        project_id=project_id,
                        bucket_name=bucket_name,
                        object_key=obj_key,
                        size=obj.size,
                        content_type="application/octet-stream" # Default, can't easily guess without head
                    )
                    await db.files.insert_one(new_file.model_dump(by_alias=True, exclude={"id"}))
                    stats["added"] += 1
                else:
                    # Check if size matches
                    db_file = db_map[obj_key]
                    if db_file["size"] != obj.size:
                        await db.files.update_one(
                            {"_id": db_file["_id"]},
                            {"$set": {"size": obj.size}}
                        )
                        stats["updated"] += 1

            # 2. Check for orphaned files (in DB but not MinIO)
            for obj_key, db_file in db_map.items():
                if obj_key not in minio_map:
                    await db.files.delete_one({"_id": db_file["_id"]})
                    stats["removed"] += 1
                    
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"ERROR syncing bucket {bucket_name}: {str(e)}")
            stats["errors"].append(f"Bucket {bucket_name}: {str(e)}")
            
    return {
        "status": "synced",
        "stats": stats
    }
