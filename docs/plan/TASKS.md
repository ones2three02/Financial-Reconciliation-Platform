# 开发任务清单 (TASKS.md)

## 任务拆解与完成状态

- [x] **TSK-001: 基础环境搭建** (输入: requirements.txt/package.json; 输出: 运行良好的前后端骨架)
- [x] **TSK-002: 数据库物理模型设计** (输入: db.py/models.py; 输出: MySQL 表结构初始化)
- [x] **TSK-003: 字段映射接口与UI** (输入: FieldMapping CRUD; 输出: 映射规则配置管理页面)
- [x] **TSK-004: 门店别名配置接口与UI** (输入: StoreAlias CRUD; 输出: 标准门店与别名绑定管理)
- [x] **TSK-005: 批量文件接收服务** (输入: FastAPI UploadFile; 输出: import_file 记录生成)
- [x] **TSK-006: Pandas 动态 Excel 解析服务** (输入: BytesIO Excel; 输出: raw_data JSON 行持久化)
- [x] **TSK-007: 清洗处理器开发** (输入: raw_data; 输出: 金额、日期、门店别名匹配并入库 clean_data)
- [x] **TSK-008: 汇总与对账引擎服务** (输入: clean_data; 输出: 对账差额自动计算与 ReconciliationResult 生成)
- [x] **TSK-009: 异常备注及处理接口与弹窗** (输入: update API; 输出: 备注录入与状态一键更新)
- [x] **TSK-010: 数据看板页面构建** (输入: API trends; 输出: ECharts 汇总折线/柱状图)
- [x] **TSK-011: 报表导出服务** (输入: pandas ExcelWriter; 输出: 标准化报表流式下载)
- [x] **TSK-012: 自动化测试集成** (输入: pytest tests/; 输出: 全链路 4 项核心测试跑通)