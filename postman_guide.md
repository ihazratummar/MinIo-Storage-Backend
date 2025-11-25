# Postman Testing Guide

## Prerequisites

1. **Create a Project** via the Admin Dashboard at `http://127.0.0.1:8000/dashboard`
2. **Copy the API Key** from the dashboard
3. **Create a Bucket** using the Bucket Management API (see below)

---

## Authentication

All API requests (except direct MinIO uploads) require authentication:

- **Header Name**: `Authorization`
- **Header Value**: `ApiKey <your-api-key>`

---

## API Endpoints

### 1. Bucket Management

#### Create Bucket
**Request**: `POST http://127.0.0.1:8000/buckets`

**Headers**:
```
Authorization: ApiKey <your-api-key>
```

**Body (JSON)**:
```json
{
    "name": "my-images"
}
```

---

#### List Buckets
**Request**: `GET http://127.0.0.1:8000/buckets`

**Headers**:
```
Authorization: ApiKey <your-api-key>
```

---

#### Rename Bucket
**Request**: `PUT http://127.0.0.1:8000/buckets/my-images`

**Headers**:
```
Authorization: ApiKey <your-api-key>
```

**Body (JSON)**:
```json
{
    "name": "my-assets"
}
```

---

#### Delete Bucket
**Request**: `DELETE http://127.0.0.1:8000/buckets/my-assets`

**Headers**:
```
Authorization: ApiKey <your-api-key>
```

---

### 2. File Upload Flow

#### Step A: Initialize Upload
**Request**: `POST http://127.0.0.1:8000/upload/init`

**Headers**:
```
Authorization: ApiKey <your-api-key>
```

**Body (JSON)**:
```json
{
    "filename": "test-image.png",
    "file_type": "image/png",
    "file_size": 1024,
    "bucket": "my-images",
    "folder": "postman-test"
}
```

**Response**:
Copy the `upload_url` and `object_key` from the response.

---

#### Step B: Upload File (Direct to MinIO)
**Request**: `PUT <paste_upload_url_here>`

- **Headers**:
    - `Content-Type`: `image/png` (Must match what you sent in Step A)
- **Body**:
    - Select **binary**
    - Choose a file to upload.

> **Note**: Do NOT send the `Authorization` header with this request. This request goes directly to MinIO, not your API.

---

#### Step C: Complete Upload
**Request**: `POST http://127.0.0.1:8000/upload/complete`

**Headers**:
```
Authorization: ApiKey <your-api-key>
```

**Body (JSON)**:
```json
{
    "object_key": "<paste_object_key_from_step_A>",
    "file_size": 1024,
    "file_type": "image/png",
    "bucket": "my-images"
}
```

**Response**:
You will get the `final_url` which is the public link to your file.

---

#### Step D: Delete File
**Request**: `DELETE http://127.0.0.1:8000/file`

**Headers**:
```
Authorization: ApiKey <your-api-key>
```

**Body (JSON)**:
```json
{
    "object_key": "<paste_object_key_from_step_A>",
    "bucket": "my-images"
}
```

---

### 3. File Access

#### Get File URL (Generate Presigned URL)
**Request**: `POST http://127.0.0.1:8000/file/url`

**Headers**:
```
Authorization: ApiKey <your-api-key>
```

**Body (JSON)**:
```json
{
    "object_key": "<your-object-key>",
    "bucket": "my-images",
    "expires_in": 3600
}
```

**Response**:
```json
{
    "url": "https://minio-api.hazratdev.top/...",
    "expires_in": 3600
}
```

> **Note**: This generates a **temporary presigned URL** that expires after the specified time (default: 1 hour). Use this URL to display/download the file.

---

## Admin Endpoints

### Create Project
**Request**: `POST http://127.0.0.1:8000/admin/projects`

**Headers**:
```
X-Admin-Secret: <your-admin-secret>
```

**Body (JSON)**:
```json
{
    "name": "My Project"
}
```

---

### List Projects
**Request**: `GET http://127.0.0.1:8000/admin/projects`

**Headers**:
```
X-Admin-Secret: <your-admin-secret>
```

**Response**: Returns all projects with metrics (bucket_count, file_count, total_size)

---

## Notes

### File Access Strategy

Your MinIO buckets are **publicly readable** for permanent access. This means:

1. **Store the `final_url`** from `/upload/complete` in your database
2. **Use it directly** - The URL works permanently without expiration
3. **No authentication needed** - Files are publicly accessible via direct URL

**Example Workflow**:
```
Upload → Get final_url → Store in DB → Use URL directly in your app
```

### Optional: Temporary URLs

If you need **temporary access** for specific files, use the `/file/url` endpoint to generate presigned URLs with custom expiration times.

### Other Notes

- The `bucket` field is **required** in all upload and delete operations
- Bucket names must be created before uploading files
- File metadata is tracked in MongoDB for metrics
- Admin secret is configured in `.env` as `ADMIN_SECRET`
- All buckets are created with public-read policy for permanent access
