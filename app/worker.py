from app.core.config import settings
import clamd
from minio import Minio
from pymongo import MongoClient
import io
import os
from PIL import Image
import subprocess
import tempfile
from pypdf import PdfReader, PdfWriter
from bson import ObjectId

# Initialize Clients
minio_client = Minio(
    endpoint=settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=settings.MINIO_SECURE
)

mongo_client = MongoClient(settings.MONGO_URI)
db = mongo_client[settings.MONGO_DB_NAME]

def get_clamav_client():
    try:
        return clamd.ClamdNetworkSocket(settings.CLAMAV_HOST, settings.CLAMAV_PORT)
    except Exception as e:
        return None

async def scan_file(bucket_name: str, object_key: str, file_id: str):
    print(f"Scanning file: {bucket_name}/{object_key} (ID: {file_id})")
    
    cd = get_clamav_client()
    if not cd:
        print("ClamAV not available, skipping scan")
        return {"status": "skipped", "reason": "ClamAV unavailable"}

    try:
        # Get file stream from MinIO
        response = minio_client.get_object(bucket_name=bucket_name, object_name=object_key)
        file_content = response.read()
        response.close()
        response.release_conn()

        # Scan with ClamAV
        # clamd expects a stream or bytes. instream() is good for streams.
        scan_result = cd.instream(io.BytesIO(file_content))
        
        status = "clean"
        result_details = "Clean"
        
        if scan_result and scan_result.get('stream') and scan_result['stream'][0] == 'FOUND':
            status = "infected"
            result_details = scan_result['stream'][1]
            print(f"VIRUS DETECTED: {result_details}")
            
            # Quarantine or Delete (for now, just mark as infected)
            # In production, you might move it to a quarantine bucket
        
        # Update MongoDB
        db.files.update_one(
            {"_id": ObjectId(file_id)},
            {"$set": {"status": status, "scan_result": result_details}}
        )
        
        return {"status": status, "file": object_key, "details": result_details}

    except Exception as e:
        print(f"Error scanning file: {e}")
        # Update DB with error
        db.files.update_one(
            {"_id": ObjectId(file_id)},
            {"$set": {"status": "error", "scan_result": str(e)}}
        )
        return {"status": "error", "error": str(e)}

async def optimize_image(bucket_name: str, object_key: str, file_id: str):
    print(f"Optimizing image: {bucket_name}/{object_key} (ID: {file_id})")
    
    try:
        # Get file from MinIO
        response = minio_client.get_object(bucket_name=bucket_name, object_name=object_key)
        file_content = response.read()
        response.close()
        response.release_conn()

        # Process with Pillow
        img = Image.open(io.BytesIO(file_content))
        
        # Convert to RGB if necessary (e.g. for PNG to JPEG/WebP)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        # Resize if too large (max 1920px width)
        max_width = 1920
        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
        # Save as WebP
        output = io.BytesIO()
        img.save(output, format="WEBP", quality=80, optimize=True)
        output.seek(0)
        
        # Upload optimized version
        optimized_key = f"{os.path.splitext(object_key)[0]}_optimized.webp"
        minio_client.put_object(
            bucket_name=bucket_name,
            object_name=optimized_key,
            data=output,
            length=output.getbuffer().nbytes,
            content_type="image/webp"
        )
        
        # Update MongoDB
        db.files.update_one(
            {"_id": ObjectId(file_id)},
            {"$set": {"status": "optimized", "optimized_version": optimized_key}}
        )
        
        return {"status": "optimized", "original": object_key, "optimized": optimized_key}

    except Exception as e:
        print(f"Error optimizing image: {e}")
        db.files.update_one(
            {"_id": ObjectId(file_id)},
            {"$set": {"status": "optimization_failed", "scan_result": str(e)}}
        )
        return {"status": "error", "error": str(e)}

async def transcode_video(bucket_name: str, object_key: str, file_id: str):
    print(f"Transcoding video: {bucket_name}/{object_key} (ID: {file_id})")
    
    try:
        # Get file from MinIO
        response = minio_client.get_object(bucket_name=bucket_name, object_name=object_key)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(object_key)[1]) as tmp_input:
            tmp_input.write(response.read())
            tmp_input_path = tmp_input.name
            
        response.close()
        response.release_conn()
        
        # Output path
        tmp_output_path = os.path.splitext(tmp_input_path)[0] + "_transcoded.mp4"
        
        # Transcode with FFmpeg
        # ffmpeg -i input -c:v libx264 -c:a aac output.mp4
        cmd = [
            "ffmpeg", "-y",
            "-i", tmp_input_path,
            "-c:v", "libx264",
            "-preset", "fast",
            "-c:a", "aac",
            tmp_output_path
        ]
        
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Upload transcoded version
        transcoded_key = f"{os.path.splitext(object_key)[0]}_transcoded.mp4"
        
        with open(tmp_output_path, "rb") as f:
            file_stat = os.stat(tmp_output_path)
            minio_client.put_object(
                bucket_name=bucket_name,
                object_name=transcoded_key,
                data=f,
                length=file_stat.st_size,
                content_type="video/mp4"
            )
            
        # Cleanup
        os.remove(tmp_input_path)
        os.remove(tmp_output_path)
        
        # Update MongoDB
        db.files.update_one(
            {"_id": ObjectId(file_id)},
            {"$set": {"status": "transcoded", "optimized_version": transcoded_key}}
        )
        
        return {"status": "transcoded", "original": object_key, "transcoded": transcoded_key}

    except Exception as e:
        print(f"Error transcoding video: {e}")
        db.files.update_one(
            {"_id": ObjectId(file_id)},
            {"$set": {"status": "transcoding_failed", "scan_result": str(e)}}
        )
        return {"status": "error", "error": str(e)}

async def sanitize_document(bucket_name: str, object_key: str, file_id: str):
    print(f"Sanitizing document: {bucket_name}/{object_key} (ID: {file_id})")
    
    try:
        # Get file from MinIO
        response = minio_client.get_object(bucket_name=bucket_name, object_name=object_key)
        file_content = io.BytesIO(response.read())
        response.close()
        response.release_conn()
        
        # Process PDF
        reader = PdfReader(file_content)
        writer = PdfWriter()
        
        for page in reader.pages:
            writer.add_page(page)
            
        # Remove metadata
        writer.add_metadata({})
        
        # Save sanitized version
        output = io.BytesIO()
        writer.write(output)
        output.seek(0)
        
        # Upload sanitized version
        sanitized_key = f"{os.path.splitext(object_key)[0]}_sanitized.pdf"
        minio_client.put_object(
            bucket_name=bucket_name,
            object_name=sanitized_key,
            data=output,
            length=output.getbuffer().nbytes,
            content_type="application/pdf"
        )
        
        # Update MongoDB
        db.files.update_one(
            {"_id": ObjectId(file_id)},
            {"$set": {"status": "sanitized", "optimized_version": sanitized_key}}
        )
        
        return {"status": "sanitized", "original": object_key, "sanitized": sanitized_key}

    except Exception as e:
        print(f"Error sanitizing document: {e}")
        db.files.update_one(
            {"_id": ObjectId(file_id)},
            {"$set": {"status": "sanitization_failed", "scan_result": str(e)}}
        )
        return {"status": "error", "error": str(e)}
