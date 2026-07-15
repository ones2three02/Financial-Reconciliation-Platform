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

@app.on_event("startup")
def on_startup():
    from backend.app.core.db import Base, engine, SessionLocal
    import backend.app.models  # 加载所有 SQLAlchemy 模型类以进行建表注册
    from backend.app.models.auth import AppUser
    from backend.app.services.auth_service import create_user
    
    # 自动执行 SQLite 表结构创建，保障离线客户端免 Migration 初始化
    Base.metadata.create_all(bind=engine)
    
    with SessionLocal() as db:
        admin_exists = db.query(AppUser).filter(AppUser.username == "admin").first()
        if not admin_exists:
            try:
                # 自动创建默认管理员账户
                create_user(
                    db,
                    username="admin",
                    password="admin_password_123",
                    role="admin"
                )
                db.commit()
                print("Database auto-seeded: default admin user created.")
                
                # 自动填充初始的标准门店数据，优化新手开箱体验
                from backend.scripts.seed_stores import main as seed_stores_main
                seed_stores_main()
            except Exception as e:
                print("Failed to auto-seed default database:", e)

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
