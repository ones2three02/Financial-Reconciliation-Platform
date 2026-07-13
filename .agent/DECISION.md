# 智能体架构决策备忘 (DECISION.md)

* **已执行决策 1**：通过 [backend/app/core/db.py](file:///Users/croodslee/Vibe%20Coding/Financial-Reconciliation-Platform/backend/app/core/db.py) 自动为用户连接本地 MySQL，并在数据库不存在时自动建立 `financial_reconciliation` 库及创建全量表结构，免去繁杂的手工导库。
* **已执行决策 2**：前端将全部类型定义更改为 `import type` 导入，彻底修复了由 Vite 编译混合导入导致的白屏语法报错。