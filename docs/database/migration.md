# 数据库迁移与回滚

项目数据库结构由 Alembic 管理，应用启动时不再自动执行 `create_all` 或 `ALTER TABLE`。
以下命令仅用于本地开发数据库；生产环境必须由运维在独立变更窗口执行，本项目不会自动触发生产迁移。

## 已有本地 SQLite 数据库升级

从项目根目录执行：

```bash
python backend/scripts/backup_sqlite.py frp.db
alembic -c backend/alembic.ini stamp 0001_existing_schema
alembic -c backend/alembic.ini upgrade head
alembic -c backend/alembic.ini current
```

执行条件：

- `frp.db` 必须是旧程序已创建且结构与 `0001_existing_schema` 一致的数据库；
- `stamp` 只登记版本，不执行建表，因此不能对空库或未知结构数据库使用；
- 备份命令成功并确认备份文件可读取后，才能继续迁移；
- 预期当前版本为 `0003_authentication_foundation (head)`。

## 新建空数据库

空数据库不得执行 `stamp`，直接运行：

```bash
alembic -c backend/alembic.ini upgrade head
```

## 回滚方案

如果 `upgrade head` 失败：

1. 立即停止应用，不继续写入；
2. 保存迁移错误日志，但不得包含业务明细或密钥；
3. 将失败数据库移出运行路径；
4. 用迁移前备份副本恢复原数据库文件；
5. 修正迁移并在副本上重新验证后，再安排下一次升级。

仅在测试数据库中验证结构降级：

```bash
alembic -c backend/alembic.ini downgrade 0001_existing_schema
```

降级会移除新增的认证、批次、完整性、提取运行和审计结构，不应用于已经产生新业务数据的正式数据库；正式回滚优先使用迁移前完整备份。
