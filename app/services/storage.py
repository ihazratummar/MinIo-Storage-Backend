from minio import Minio
from datetime import timedelta
from app.core.config import settings

class StorageService:
    def __init__(self):
        self.client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )

    def generate_presigned_url(self, bucket_name: str, object_name: str, method: str = "PUT") -> str:
        # method argument is ignored if we use presigned_put_object, 
        # but we keep the signature for compatibility or just use it.
        if method != "PUT":
             # Fallback for other methods if needed, or just error.
             return self.client.get_presigned_url(
                method=method,
                bucket_name=bucket_name,
                object_name=object_name,
                expires=timedelta(seconds=settings.PRESIGNED_EXPIRY),
            )
            
        return self.client.presigned_put_object(
            bucket_name=bucket_name,
            object_name=object_name,
            expires=timedelta(seconds=settings.PRESIGNED_EXPIRY),
        )

    def check_object_exists(self, bucket_name: str, object_name: str) -> bool:
        try:
            self.client.stat_object(bucket_name=bucket_name, object_name=object_name)
            return True
        except Exception:
            return False

    def delete_object(self, bucket_name: str, object_name: str):
        self.client.remove_object(bucket_name=bucket_name, object_name=object_name)

    def get_object_stats(self, bucket_name: str, object_name: str):
        return self.client.stat_object(bucket_name=bucket_name, object_name=object_name)

storage_service = StorageService()
