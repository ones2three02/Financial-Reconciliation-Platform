# 数据库迁移说明 (migration.md)

## 迁移指南
* 项目使用 SQLAlchemy 声明式映射，配合 FastAPI 启动时的 `Base.metadata.create_all` 自动建表逻辑，极大降低本地测试部署门槛。
* 在生产 MySQL 环境下，应当使用 Alembic 进行结构迭代控制：
  ```bash
  alembic init migrations
  alembic revision --autogenerate -m "Init tables"
  alembic upgrade head
  ```