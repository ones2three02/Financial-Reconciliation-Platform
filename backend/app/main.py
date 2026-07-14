from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api import auth, batches, dashboard, files, mappings, preflight, reconciliation, stores
from backend.app.api.auth import get_current_user
from backend.app.core.config import settings


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_cors_origins,
    allow_credentials=False,
    allow_headers=["Authorization", "Content-Type"],
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
)

authenticated = [Depends(get_current_user)]
app.include_router(
    stores.router,
    prefix=f"{settings.API_V1_STR}/stores",
    tags=["stores"],
    dependencies=authenticated,
)
app.include_router(
    mappings.router,
    prefix=f"{settings.API_V1_STR}/mappings",
    tags=["mappings"],
    dependencies=authenticated,
)
app.include_router(
    files.router,
    prefix=f"{settings.API_V1_STR}/files",
    tags=["files"],
    dependencies=authenticated,
)
app.include_router(
    preflight.router,
    prefix=f"{settings.API_V1_STR}/files",
    tags=["files"],
    dependencies=authenticated,
)
app.include_router(
    batches.router,
    prefix=f"{settings.API_V1_STR}/batches",
    tags=["batches"],
    dependencies=authenticated,
)
app.include_router(
    reconciliation.router,
    prefix=f"{settings.API_V1_STR}/reconciliation",
    tags=["reconciliation"],
    dependencies=authenticated,
)
app.include_router(
    dashboard.router,
    prefix=f"{settings.API_V1_STR}/dashboard",
    tags=["dashboard"],
    dependencies=authenticated,
)
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])


@app.get("/")
def root():
    return {"message": "Financial Reconciliation Platform API"}
