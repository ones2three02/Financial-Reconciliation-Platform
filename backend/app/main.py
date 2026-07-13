from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.core.db import engine, Base, SessionLocal
from backend.app.models.store import Store
from backend.app.api import stores, mappings, files, reconciliation, dashboard, auth

# Create tables automatically on startup for easy MVP setup
# In production, Alembic migrations are used
Base.metadata.create_all(bind=engine)

# Safely run table columns check and migration for MVP
def run_migrations():
    from sqlalchemy import inspect, text
    db = SessionLocal()
    try:
        inspector = inspect(engine)
        columns = [c['name'] for c in inspector.get_columns('store')]
        
        # Check and add columns
        if 'code' not in columns:
            db.execute(text("ALTER TABLE store ADD COLUMN code VARCHAR(50) NULL;"))
        if 'region' not in columns:
            db.execute(text("ALTER TABLE store ADD COLUMN region VARCHAR(100) NULL;"))
        if 'manager' not in columns:
            db.execute(text("ALTER TABLE store ADD COLUMN manager VARCHAR(50) NULL;"))
        if 'phone' not in columns:
            db.execute(text("ALTER TABLE store ADD COLUMN phone VARCHAR(50) NULL;"))
        db.commit()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Database migration failed: {e}")
    finally:
        db.close()

run_migrations()

from backend.app.models.store import Store, StoreAlias

# Seed the 22 standard stores if the table is empty
def seed_stores():
    db = SessionLocal()
    try:
        default_stores = [
            "蚌埠吾悦店", "蚌埠银泰店", "淮北吾悦店", "淮南吾悦店", "宿州吾悦店",
            "颍上店", "华农店", "荆州店", "荆州二店", "民院店",
            "杨家湾", "财富中心店", "钟祥店", "高新吾悦店", "进贤吾悦店",
            "新力店", "新余二店", "新余店", "旭辉店", "瑶湖店",
            "宜春店", "阜阳宝龙店"
        ]
        
        if db.query(Store).count() == 0:
            for idx, name in enumerate(default_stores):
                code = f"MD{str(idx + 1).zfill(3)}"
                db.add(Store(name=name, code=code))
            db.commit()
            
        # Backfill codes for any existing stores whose codes are null or empty
        all_stores = db.query(Store).order_by(Store.id).all()
        for idx, s in enumerate(all_stores):
            if not s.code:
                s.code = f"MD{str(idx + 1).zfill(3)}"
        db.commit()
            
        # Seed example store aliases for testing & automatic mapping
        aliases_map = {
            "山道曙光游泳馆(曙光商贸城民族大道店)": "民院店",
            "山道健身－民院健身房": "民院店",
            "山道健身－民院游泳馆": "民院店",
            "山道健身会所-宜春店": "宜春店",
            "山道健身游泳(宜春润达店)": "宜春店",
            "山道健身游泳(新余店)": "新余店",
            "新余 : 山道健身游泳高奢店(新余上亿广场店)": "新余店",
            "南昌 : 山道健身游泳(南昌高新吾悦广场店)": "高新吾悦店"
        }
        for alias_name, store_name in aliases_map.items():
            store = db.query(Store).filter(Store.name == store_name).first()
            if store:
                exists = db.query(StoreAlias).filter(StoreAlias.alias_name == alias_name).first()
                if not exists:
                    db.add(StoreAlias(alias_name=alias_name, store_id=store.id, status="mapped"))
        db.commit()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to seed stores or aliases: {e}")
    finally:
        db.close()

seed_stores()

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
