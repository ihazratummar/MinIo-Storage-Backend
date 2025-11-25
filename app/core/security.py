from fastapi import Security, HTTPException, status, Depends
from fastapi.security import APIKeyHeader
from app.core.database import get_db
from app.models.project import Project

api_key_header = APIKeyHeader(name="Authorization", auto_error=False)

async def get_current_project(
    api_key_header: str = Security(api_key_header),
    db = Depends(get_db)
) -> Project:
    if not api_key_header:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    
    # Handle "ApiKey <key>" format or just "<key>"
    if api_key_header.startswith("ApiKey "):
        token = api_key_header.split(" ")[1]
    else:
        token = api_key_header

    project_data = await db.projects.find_one({"api_key": token})
    if not project_data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key",
        )
    return Project(**project_data)

admin_secret_header = APIKeyHeader(name="X-Admin-Secret", auto_error=False)

async def verify_admin(
    secret: str = Security(admin_secret_header)
):
    from app.core.config import settings
    if not secret or secret != settings.ADMIN_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Admin Secret",
        )
    return True
