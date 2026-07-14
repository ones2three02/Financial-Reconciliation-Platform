# 导入文件替换、作废与整批重置实施计划

> **执行要求：** 实施时使用 `superpowers:executing-plans`；若项目规则允许，也可使用 `superpowers:subagent-driven-development`。本项目当前按用户要求在同一会话内直接执行，不启用子代理。

**目标：** 在不物理删除历史数据的前提下，实现指定文件替换、指定文件作废和账期当前数据整批重置，确保重导不会重复计数，失败替换不会破坏原有效版本。

**架构：** 复用现有 `ImportFile.is_current` 和 `supersedes_file_id` 建立文件版本链。把导入管线拆分为“事务内导入”和“对外提交”两层；替换服务在一个数据库事务内完成新文件提取、旧版本退役、覆盖范围刷新、自动对账和审计。作废与重置通过统一的当前版本退役逻辑完成，不新增数据库表或迁移。

**技术栈：** FastAPI、SQLAlchemy 2、Pydantic v2、pytest、Vue 3、TypeScript、Axios、现有 shadcn-vue 风格组件。

## 全局约束

- 不修改数据库结构，不新增第三方依赖。
- 原始文件、`RawData`、历史 `CleanData` 和历史提取运行永久保留。
- 已关账批次必须先重开；替换、作废、重置均由服务端会话确定操作人。
- 通联、美团、抖音按整份文件替换；门店财务表整份替换并同时刷新销售和现金。
- 未知门店不会自动匹配；替换后的新文件可进入待处理状态，但旧错误金额不得继续参与当前对账。
- 每个任务先写失败测试，再写最小实现，通过后再重构；每次提交只包含一个明确目的。

---

## 任务 1：建立版本操作测试骨架和请求模型

**文件：**

- 新建：`backend/tests/test_import_versioning.py`
- 修改：`backend/app/schemas/import_command.py`

### 步骤

- [ ] 在 `test_import_versioning.py` 建立批次、门店、别名、财务工作簿和渠道工作簿辅助函数，复用现有 fixture 风格，不复制生产逻辑。
- [ ] 先添加请求校验失败测试：空原因、超过 500 字原因、整批重置确认日期缺失。
- [ ] 运行：`venv/bin/python -m pytest backend/tests/test_import_versioning.py -q`，确认因模型不存在而失败。
- [ ] 在 `import_command.py` 增加 `InvalidateImportRequest`、`ResetBatchCurrentDataRequest` 和版本操作返回模型；原因统一去除首尾空白并限制 1–500 字。
- [ ] 再运行同一测试，确认请求模型测试通过。
- [ ] 提交：`test: 建立导入版本操作测试骨架`

## 任务 2：拆分可复用的事务内导入管线

**文件：**

- 修改：`backend/app/services/import_pipeline.py`
- 修改：`backend/tests/test_import_pipeline.py`

### 步骤

- [ ] 添加测试：事务内导入可指定 `supersedes_file_id`，但普通 `import_workbook` 的现有行为和返回值不变。
- [ ] 添加测试：替换场景可在判重时排除被替换文件，但仍会识别同业务范围的其他当前重复文件。
- [ ] 运行：`venv/bin/python -m pytest backend/tests/test_import_pipeline.py -q`，确认新测试失败。
- [ ] 提取私有事务内函数，使其只 `flush` 不 `commit`，参数显式包含 `supersedes_file_id` 和判重排除 ID。
- [ ] 保留公开 `import_workbook` 作为事务边界，确保已有导入 API 无行为回归。
- [ ] 运行：`venv/bin/python -m pytest backend/tests/test_import_pipeline.py -q`，确认全部通过。
- [ ] 提交：`refactor: 拆分事务内工作簿导入管线`

## 任务 3：实现当前版本退役和覆盖范围刷新

**文件：**

- 修改：`backend/app/services/coverage_service.py`
- 新建：`backend/app/services/import_version_service.py`
- 修改：`backend/tests/test_import_versioning.py`

### 步骤

- [ ] 添加失败测试：作废财务文件后销售和现金覆盖恢复为 `missing`，历史文件、原始行和标准行仍存在，但均不再参与当前汇总。
- [ ] 添加失败测试：若同一范围仍有其他当前文件，作废只减去目标文件金额，覆盖仍为 `present_data`。
- [ ] 添加失败测试：目标文件不是当前版本或批次已关账时返回冲突。
- [ ] 运行版本测试，确认失败。
- [ ] 在覆盖服务中增加按“批次 + 门店 + 来源”重建覆盖的公共函数：金额来自当前有效 `CleanData`；门店财务表当前文件可为销售/现金提供文件级零证据；渠道没有当前有效行时保持 `missing`。
- [ ] 在版本服务实现作用域收集、文件/提取运行/标准数据退役、开放质量问题转为 `superseded`、自动对账和 `file_invalidated` 审计。
- [ ] 用单一数据库事务提交，异常时整体回滚。
- [ ] 运行：`venv/bin/python -m pytest backend/tests/test_import_versioning.py -q`。
- [ ] 提交：`feat: 支持作废当前导入文件`

## 任务 4：实现原子文件替换

**文件：**

- 修改：`backend/app/services/import_version_service.py`
- 修改：`backend/app/services/import_pipeline.py`
- 修改：`backend/tests/test_import_versioning.py`

### 步骤

- [ ] 添加失败测试：替换财务文件后销售与现金只统计新版本，新文件指向旧文件，旧文件和旧标准数据退出当前版本。
- [ ] 添加失败测试：渠道文件替换会移除旧文件影响范围并启用新文件影响范围，覆盖刷新使用新旧门店/来源并集。
- [ ] 添加失败测试：预检或提取硬失败时事务回滚，旧文件仍为当前版本，金额不变。
- [ ] 添加失败测试：新文件与目标文件内容相同返回 400；与同业务范围另一当前文件内容相同返回 409。
- [ ] 添加失败测试：新文件出现未知门店时旧文件退出当前计算，新文件和批次进入待处理状态。
- [ ] 运行版本测试，确认失败。
- [ ] 实现 `replace_import_file`：锁定并校验目标、继承批次/模板/文件级门店、事务内导入新文件、退役旧版本、刷新新旧作用域、自动对账、记录 `file_replaced` 审计。
- [ ] 确保硬错误发生在旧版本退役前，且整个操作只提交一次。
- [ ] 运行：`venv/bin/python -m pytest backend/tests/test_import_versioning.py backend/tests/test_import_pipeline.py backend/tests/test_channel_extraction.py -q`。
- [ ] 提交：`feat: 支持原子替换导入文件`

## 任务 5：实现账期当前数据整批重置

**文件：**

- 修改：`backend/app/services/import_version_service.py`
- 修改：`backend/tests/test_import_versioning.py`

### 步骤

- [ ] 添加失败测试：确认日期与业务日期不一致时拒绝且数据不变。
- [ ] 添加失败测试：重置后所有当前文件、提取运行和标准数据均退出当前版本，历史数据仍存在。
- [ ] 添加失败测试：已有 `present_zero` 人工证据也恢复为 `missing`，所有结果重算为 `incomplete`，批次为 `attention_required` 且版本加一。
- [ ] 添加失败测试：已关账批次拒绝重置。
- [ ] 运行版本测试，确认失败。
- [ ] 实现 `reset_batch_current_data`，批量退役当前数据、关闭开放质量问题、重置覆盖、自动对账并写入 `batch_current_data_reset` 审计。
- [ ] 运行：`venv/bin/python -m pytest backend/tests/test_import_versioning.py backend/tests/test_reconciliation_batch.py -q`。
- [ ] 提交：`feat: 支持重置账期当前数据`

## 任务 6：开放 API 并扩展批次详情

**文件：**

- 修改：`backend/app/api/files.py`
- 修改：`backend/app/api/batches.py`
- 修改：`backend/app/schemas/batch.py`
- 修改：`backend/app/schemas/import_command.py`
- 修改：`backend/tests/test_api_contracts.py`
- 修改：`backend/tests/test_batch_queries.py`

### 步骤

- [ ] 添加失败测试：`POST /files/{id}/replace` 接收文件和原因，模板、批次、门店由旧文件继承。
- [ ] 添加失败测试：`POST /files/{id}/invalidate` 和 `POST /batches/{id}/reset-current-data` 使用当前登录用户作为 actor。
- [ ] 添加失败测试：HTTP 状态按设计映射为 400、404、409，而不是泄露内部异常。
- [ ] 添加失败测试：批次详情同时返回当前和历史文件，并包含 `is_current`、`supersedes_file_id`。
- [ ] 运行 API 和查询测试，确认失败。
- [ ] 增加三个路由、依赖注入和请求/返回模型；不接受客户端 actor、profile 或 store 覆盖。
- [ ] 修改批次详情查询，移除只查当前文件的过滤条件，按版本状态与时间稳定排序。
- [ ] 运行：`venv/bin/python -m pytest backend/tests/test_api_contracts.py backend/tests/test_batch_queries.py -q`。
- [ ] 提交：`feat: 开放导入版本管理接口`

## 任务 7：实现前端替换、作废和重置交互

**文件：**

- 修改：`frontend/src/services/api.ts`
- 修改：`frontend/src/views/ImportCenter.vue`
- 视需要修改：`frontend/src/views/ReconciliationList.vue`

### 步骤

- [ ] 在 API 类型中为 `ImportFile` 增加必填 `is_current` 和 `supersedes_file_id`，增加替换、作废、整批重置方法。
- [ ] 导入记录默认展示当前文件，提供“显示历史版本”切换；每行明确展示当前/历史状态及被替换关系。
- [ ] 当前文件且批次未关账时显示“替换”和“作废”；历史文件无操作按钮。
- [ ] 替换弹窗要求选择 `.xlsx` 并填写原因，展示“沿用原模板和门店”的提示。
- [ ] 作废弹窗要求填写原因，提示金额将退出当前对账但历史仍保留。
- [ ] 批次卡片增加“重置当日当前数据”，要求填写原因并输入完整业务日期确认。
- [ ] 操作成功后统一刷新批次、覆盖、质量问题和对账结果；错误优先显示后端中文 `detail`。
- [ ] 运行：`cd frontend && npm run build`，修复所有 TypeScript 和构建错误。
- [ ] 提交：`feat: 增加重导和账期重置操作界面`

## 任务 8：回归、样例验收和代码审查

**文件：**

- 视审查结果修改与本功能直接相关的文件。

### 步骤

- [ ] 运行后端完整测试：`venv/bin/python -m pytest -q`。
- [ ] 运行民院店样例验收：`venv/bin/python -m pytest backend/tests/test_example_acceptance.py -q`。
- [ ] 运行前端生产构建：`cd frontend && npm run build`。
- [ ] 按代码审查清单检查：事务边界、并发判重、历史保留、权限、错误码、actor 来源、未知门店、财务双来源覆盖、无物理删除。
- [ ] 检查工作树：`git diff --check`、`git status --short`，确认没有临时文件、密钥、数据库和构建产物进入提交。
- [ ] 如审查发现问题，先补失败测试再修复，并重复完整验证。
- [ ] 提交：`test: 完善导入版本管理回归验证`（仅在确有测试或修复变更时创建）。

## 完成标准

- 用户能在页面明确选择追加、替换、作废或整批重置。
- 替换和作废后当前金额、覆盖矩阵、质量问题和对账结果立即一致。
- 任意失败替换都不会让旧有效数据丢失或产生双计。
- 所有历史数据和版本关系可查询，操作原因和服务端登录人可审计。
- 后端完整测试、民院样例测试、前端生产构建全部通过。
