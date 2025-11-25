# MinIO FastAPI Backend

A production-ready, multi-tenant file storage backend using **FastAPI**, **MongoDB**, and **MinIO**.

## Features

- ✅ **Multi-Tenant Architecture**: Isolated projects with unique API keys
- ✅ **Dynamic Bucket Management**: Create, rename, and delete buckets via API
- ✅ **Direct Uploads**: Presigned URLs for high-performance uploads
- ✅ **Public File Access**: Permanent URLs with no expiration
- ✅ **Admin Dashboard**: Modern Vue.js + Tailwind CSS interface
- ✅ **Project Metrics**: Real-time tracking of buckets, files, and storage
- ✅ **Optimized Performance**: Single-query aggregation pipeline
- ✅ **Responsive Design**: Mobile-friendly admin panel
- ✅ **Secure**: Admin authentication with secret key

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
Copy `.env.example` to `.env` and update with your credentials:
```env
MINIO_ENDPOINT=your-minio-endpoint
MINIO_ACCESS_KEY=your-access-key
MINIO_SECRET_KEY=your-secret-key
MONGO_URI=your-mongodb-uri
ADMIN_SECRET=your-admin-secret
```

### 3. Create Database Indexes
```bash
python create_indexes.py
```

### 4. Run the Server
```bash
uvicorn main:app --reload
```

### 5. Access Dashboard
Visit: [http://127.0.0.1:8000/dashboard](http://127.0.0.1:8000/dashboard)

## API Documentation

### Admin Endpoints
- `POST /admin/projects` - Create a new project
- `GET /admin/projects` - List all projects with metrics
- `DELETE /admin/projects/{id}` - Delete project and all data

### Bucket Management
- `POST /buckets` - Create a bucket
- `GET /buckets` - List buckets
- `PUT /buckets/{name}` - Rename bucket
- `DELETE /buckets/{name}` - Delete bucket

### File Operations
- `POST /upload/init` - Initialize upload (get presigned URL)
- `POST /upload/complete` - Complete upload (save metadata)
- `DELETE /file` - Delete file
- `POST /file/url` - Generate temporary presigned URL (optional)

## Project Structure

```
MinioApi/
├── app/
│   ├── api/          # API endpoints
│   ├── core/         # Configuration, database, security
│   ├── models/       # Pydantic models
│   ├── schemas/      # Request/response schemas
│   ├── services/     # Business logic (storage)
│   └── dashboard/    # Admin UI
├── main.py           # Application entry point
├── create_indexes.py # Database optimization script
├── postman_guide.md  # API testing guide
└── requirements.txt  # Python dependencies
```

## Performance

- **Optimized Queries**: Single aggregation pipeline for all projects
- **Database Indexes**: 5 indexes for fast lookups
- **Response Time**: Sub-100ms for project listing
- **Scalability**: Handles 1000+ projects efficiently

## Security

- Admin panel protected by secret key
- API key authentication for all client operations
- Public-read bucket policy for permanent file access
- Cascade deletion prevents orphaned data

## Documentation

- **API Guide**: See `postman_guide.md` for detailed API usage
- **Interactive Docs**: Visit `/docs` for Swagger UI
- **Alternative Docs**: Visit `/redoc` for ReDoc UI

## License

MIT
# MinIo-Storage-Backend
