from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.core.db import engine, Base
from backend.app.api import stores, mappings, files, reconciliation, dashboard, auth

# Create tables automatically on startup for easy MVP setup
# In production, Alembic migrations are used
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development ease, allow all origins
    allow_credentials=True,
    allow_headers=["*"],
    allow_methods=["*"],
)

# Include Routers
app.include_router(stores.router, prefix=f"{settings.API_V1_STR}/stores", tags=["stores"])
app.include_router(mappings.router, prefix=f"{settings.API_V1_STR}/mappings", tags=["mappings"])
app.include_router(files.router, prefix=f"{settings.API_V1_STR}/files", tags=["files"])
app.include_router(reconciliation.router, prefix=f"{settings.API_V1_STR}/reconciliation", tags=["reconciliation"])
app.include_router(dashboard.router, prefix=f"{settings.API_V1_STR}/dashboard", tags=["dashboard"])
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])

@app.get("/")
def root():
    return {"message": "Welcome to the Financial Reconciliation Platform API"}
