from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from app.api.routes import router as api_router
from app.api.admin import router as admin_router
from app.api.buckets import router as buckets_router
from app.core.database import db

app = FastAPI(title="MinIO File Backend")

@app.on_event("startup")
async def on_startup():
    db.connect()

@app.on_event("shutdown")
async def on_shutdown():
    db.close()

app.include_router(api_router)
app.include_router(admin_router, prefix="/admin", tags=["Admin"])
app.include_router(buckets_router, tags=["Buckets"])

app.mount("/dashboard", StaticFiles(directory="app/dashboard", html=True), name="dashboard")

@app.get("/")
async def root():
    return RedirectResponse(url="/dashboard")

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    from fastapi import Response
    return Response(status_code=204)
