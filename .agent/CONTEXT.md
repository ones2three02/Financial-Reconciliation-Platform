# 智能体上下文 (CONTEXT.md)

## 当前项目上下文
* **开发语言**：Python 3.14.6 + TypeScript
* **主要依赖**：FastAPI + SQLAlchemy 2.x + PyMySQL + Pandas + Vue 3 + Vite + TailwindCSS v3 + ECharts
* **数据库连接**：本地 MySQL 8 (`financial_reconciliation` 库，用户密码: `root-0213`)
* **对账日期缺省公式**：Expected (通联 + 美团 + 抖音) == Actual (销售 - 现金)