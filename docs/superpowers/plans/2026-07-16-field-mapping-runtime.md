# 字段映射全链路生效 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让字段映射配置确定性地作用于预检、首次导入、替换和历史恢复，并覆盖四个输入来源的全部计算字段。

**Architecture:** 新增纯函数列绑定解析器，把模板声明的标准字段、数据库别名和实际 Excel 表头解析成不可变绑定；预检和导入共同使用该解析器。导入将绑定写入每条 `RawData` 的保留元数据，提取和历史恢复只消费快照，避免配置漂移。

**Tech Stack:** Python 3.11+、FastAPI、SQLAlchemy 2、Alembic、openpyxl、pytest、Vue 3、TypeScript、Node test runner

## Global Constraints

- 同一目标字段允许多个启用别名；同一文件命中多个别名必须报冲突。
- 美团正式日期列是“验券/退款/调整时间”，“验券/退款/”是兼容别名。
- 工作表名称和表头行继续由版本化模板固定，不做模糊工作表或表头探测。
- 清理全部旧字段映射并写入 14 条新默认映射；不删除表、不改变表结构。
- `cash`、`sales` 不再是字段映射输入来源，统一使用 `store_finance`。
- 历史恢复不得查询当前字段映射，必须使用导入时快照。
- 不修改现有对账公式和门店别名解析规则。
- 不提交、推送、创建标签或发布，除非用户另行明确授权。

---

## 文件结构

- `backend/app/domain/extraction_profiles.py`：声明标准字段角色和默认列名。
- `backend/app/services/field_binding.py`：字段配置校验、别名查询、表头绑定解析、快照读取。
- `backend/app/services/workbook_preflight.py`：通过绑定完成结构和日期预检。
- `backend/app/services/import_pipeline.py`：解析绑定并写入 `_frp_field_bindings` 快照。
- `backend/app/services/extraction_engine.py`：只通过快照读取日期、门店、金额和付款方式。
- `backend/app/services/workbook_rows.py`：使用字段绑定识别汇总行。
- `backend/app/api/preflight.py`：把数据库会话传入预检。
- `backend/app/crud/field_mapping.py`、`backend/app/api/mappings.py`：集中验证字段配置。
- `backend/migrations/versions/0004_field_mapping_runtime.py`：清理旧配置并写入 14 条默认映射。
- `frontend/src/services/fieldMappingOptions.ts`：来源到目标字段的前端共享声明。
- `frontend/src/views/MappingSettings.vue`：动态来源/字段 UI 和明确错误反馈。

### Task 1: 标准字段模板与纯列绑定解析器

**Files:**
- Modify: `backend/app/domain/extraction_profiles.py`
- Create: `backend/app/services/field_binding.py`
- Create: `backend/tests/test_field_binding.py`

**Interfaces:**
- Produces: `FIELD_BINDINGS_KEY = "_frp_field_bindings"`。
- Produces: `resolve_field_bindings(profile, headers, mappings) -> dict[str, str]`。
- Produces: `bindings_from_raw_content(profile, content) -> dict[str, str]`。
- Produces: `allowed_target_fields(data_source) -> tuple[str, ...]`。

- [ ] **Step 1: 为默认、自定义、冲突和停用语义写失败测试**

创建 `backend/tests/test_field_binding.py`，覆盖：

```python
def test_tonglian_custom_store_alias_replaces_default():
    profile = get_profile("tonglian_v1")
    mappings = [mapping("tonglian", "trade_date", "统计日期"),
                mapping("tonglian", "store_name", "门店名称"),
                mapping("tonglian", "amount", "成功交易金额")]
    assert resolve_field_bindings(
        profile,
        ["统计日期", "门店名称", "成功交易金额"],
        mappings,
    )["store_name"] == "门店名称"


def test_two_store_aliases_in_same_file_are_rejected():
    profile = get_profile("tonglian_v1")
    mappings = [mapping("tonglian", "trade_date", "统计日期"),
                mapping("tonglian", "store_name", "门店名"),
                mapping("tonglian", "store_name", "门店名称"),
                mapping("tonglian", "amount", "成功交易金额")]
    with pytest.raises(FieldBindingConflictError, match="门店名.*门店名称"):
        resolve_field_bindings(
            profile,
            ["统计日期", "门店名", "门店名称", "成功交易金额"],
            mappings,
        )
```

同时测试：无来源配置时使用默认值、来源存在配置时不回退默认、停用项不匹配、重复物理表头冲突、美团两个日期别名分别命中、保留键表头被拒绝。

- [ ] **Step 2: 运行测试并确认 RED**

Run: `PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -p no:cacheprovider backend/tests/test_field_binding.py -q`

Expected: FAIL，`field_binding` 模块和新模板字段不存在。

- [ ] **Step 3: 把模板改为标准字段声明**

`ProfileDefinition` 增加并使用以下字段：

```python
default_columns: tuple[tuple[str, str], ...]
required_fields: tuple[str, ...]
date_field: str
store_field: str | None
amount_fields: tuple[str, ...]
payment_method_field: str | None = None
```

四个模板分别声明：

```python
store_finance: trade_date=日期, amount=金额, payment_method=付款方式
douyin: trade_date=核销时间, store_name=核销门店, amount=订单实收
meituan: trade_date=验券/退款/调整时间, store_name=消费门店,
         amount=总收入（元）, marketing_fee=商家营销费用（元）
tonglian: trade_date=统计日期, store_name=门店名, amount=成功交易金额
```

- [ ] **Step 4: 实现严格解析器**

`resolve_field_bindings` 必须：

```python
def resolve_field_bindings(
    profile: ProfileDefinition,
    headers: Sequence[str],
    mappings: Sequence[FieldMapping],
) -> dict[str, str]:
    # 清理表头；拒绝保留键；统计物理出现次数
    # mappings 为空时使用 profile.default_columns
    # mappings 非空时按 target_field 收集 active source_column
    # 每个 required_field 恰好命中一列，否则抛 Missing/Conflict
```

定义 `FieldBindingError`、`FieldBindingMissingError`、`FieldBindingConflictError`，错误文字包含来源、标准字段和候选/命中列名，不包含数据行。

`bindings_from_raw_content` 优先验证并返回 `_frp_field_bindings`；旧行无快照时返回模板默认绑定。

- [ ] **Step 5: 验证解析器 GREEN**

Run: `PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -p no:cacheprovider backend/tests/test_field_binding.py -q`

Expected: 所有字段绑定测试通过。

### Task 2: 字段映射配置校验与默认数据迁移

**Files:**
- Modify: `backend/app/crud/field_mapping.py`
- Modify: `backend/app/api/mappings.py`
- Modify: `backend/app/schemas/field_mapping.py`
- Create: `backend/migrations/versions/0004_field_mapping_runtime.py`
- Modify: `backend/tests/test_master_data_safety.py`
- Modify: `backend/tests/test_api_contracts.py`
- Modify: `backend/tests/test_migrations.py`

**Interfaces:**
- Consumes: `validate_field_mapping_values(data_source, target_field, source_column)`。
- Produces: 只允许四个输入来源及其标准字段的 CRUD。

- [ ] **Step 1: 写非法组合和迁移失败测试**

增加测试：

```python
with pytest.raises(ValueError, match="不支持的目标字段"):
    create_field_mapping(db, FieldMappingCreate(
        data_source="tonglian",
        target_field="payment_method",
        source_column="付款方式",
    ))
```

迁移测试先升到 `0003_authentication_foundation`，插入旧 `cash/sales` 和自定义记录，再升到 head，断言只剩 14 条默认记录，来源集合为四个新来源，美团日期有两个别名，Alembic head 为 `0004_field_mapping_runtime`。

- [ ] **Step 2: 运行定向测试并确认 RED**

Run: `PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -p no:cacheprovider backend/tests/test_master_data_safety.py backend/tests/test_api_contracts.py backend/tests/test_migrations.py -q`

Expected: 新断言失败，当前 CRUD 接受非法组合且 head 仍为 0003。

- [ ] **Step 3: 在 CRUD 创建和 API 更新中集中校验**

创建时清理三个字符串并验证。更新时用“现有值 + 请求值”计算最终组合，先校验、再查重、最后写入；重复组合返回 400，不覆盖另一记录。保留“重复创建不重新启用停用项”语义。

- [ ] **Step 4: 实现 0004 数据迁移**

迁移 `upgrade()`：

```python
op.execute(sa.text("DELETE FROM field_mapping"))
op.bulk_insert(field_mapping_table, DEFAULT_FIELD_MAPPINGS)
```

14 条包括：通联 3、抖音 3、美团 5（两个日期别名）、门店财务表 3。`downgrade()` 清空该表。

- [ ] **Step 5: 验证配置和迁移 GREEN**

Run: `PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -p no:cacheprovider backend/tests/test_master_data_safety.py backend/tests/test_api_contracts.py backend/tests/test_migrations.py -q`

Expected: 所有测试通过，桌面新库 head 为 0004。

### Task 3: 让预检消费数据库字段映射

**Files:**
- Modify: `backend/app/services/workbook_preflight.py`
- Modify: `backend/app/api/preflight.py`
- Modify: `backend/tests/test_workbook_preflight.py`
- Modify: `backend/tests/test_api_contracts.py`

**Interfaces:**
- Changes: `preflight_workbook(db, content, profile_code, business_date, store_id)`。
- Consumes: `get_mappings_by_source(db, profile.input_source, is_active_only=False)`。

- [ ] **Step 1: 写通联别名和冲突预检测试**

测试在数据库加入完整通联配置，其中 `store_name=门店名称`，构造只含“门店名称”的工作簿并断言预检成功。再启用“门店名”，构造同时含两列的工作簿，断言 `TemplateMismatchError` 包含“字段冲突”。

- [ ] **Step 2: 运行预检测试并确认 RED**

Run: `PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -p no:cacheprovider backend/tests/test_workbook_preflight.py -q`

Expected: 别名文件仍被判缺少“门店名”。

- [ ] **Step 3: 用统一绑定替换硬编码表头查找**

预检读取表头后调用 `resolve_field_bindings`，再通过绑定得到日期和门店索引。缺失/冲突转换为 `TemplateMismatchError`。移除美团包含匹配特例。汇总行识别传入绑定。

API 不再 `del db`，而是把 `db` 传入服务。

- [ ] **Step 4: 更新所有调用点并验证 GREEN**

Run: `rg -n 'preflight_workbook\(' backend -g '*.py'`

逐个更新为传入测试会话或 API 会话。

Run: `PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -p no:cacheprovider backend/tests/test_workbook_preflight.py backend/tests/test_api_contracts.py -q`

Expected: 所有预检和 API 测试通过。

### Task 4: 导入写入绑定快照并让提取只消费快照

**Files:**
- Modify: `backend/app/services/import_pipeline.py`
- Modify: `backend/app/services/extraction_engine.py`
- Modify: `backend/app/services/workbook_rows.py`
- Modify: `backend/tests/test_channel_extraction.py`
- Modify: `backend/tests/test_finance_extraction.py`
- Modify: `backend/tests/test_import_pipeline.py`

**Interfaces:**
- Changes: `_persist_raw_rows(..., bindings: Mapping[str, str])`。
- Changes: `is_summary_row(profile, content, bindings)`。
- Snapshot: 每条新 `RawData.content[FIELD_BINDINGS_KEY]` 为相同 `dict[str, str]`。

- [ ] **Step 1: 写通联完整导入快照测试**

配置 `store_name=门店名称`，导入对应工作簿，断言：

```python
raw = db_session.query(RawData).filter_by(import_file_id=outcome.import_file_id).one()
assert raw.content[FIELD_BINDINGS_KEY] == {
    "trade_date": "统计日期",
    "store_name": "门店名称",
    "amount": "成功交易金额",
}
assert source_amount(...) == Decimal("100.00")
```

- [ ] **Step 2: 写美团正式日期与财务付款方式别名测试**

美团用“验券/退款/调整时间”完成导入并验证 `amount + marketing_fee`。门店财务表配置 `payment_method=支付渠道`，验证“现金”仍生成 cash，其他渠道只生成 sales。

- [ ] **Step 3: 运行提取测试并确认 RED**

Run: `PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -p no:cacheprovider backend/tests/test_channel_extraction.py backend/tests/test_finance_extraction.py backend/tests/test_import_pipeline.py -q`

Expected: 自定义列名在硬编码预检或提取处失败。

- [ ] **Step 4: 在导入事务内解析一次并持久化快照**

`import_workbook_in_transaction` 获取完整来源映射，解析实际表头绑定，把绑定传给 `_persist_raw_rows`。每行字典增加：

```python
content_row[FIELD_BINDINGS_KEY] = dict(bindings)
```

汇总行判断必须使用相同绑定，避免通联汇总被误持久化。

- [ ] **Step 5: 提取引擎通过标准字段角色读值**

每个文件先从首条原始行得到并验证绑定，后续行必须快照一致。

门店财务表：

```python
date_col = bindings[profile.date_field]
amount_col = bindings[profile.amount_fields[0]]
payment_col = bindings[profile.payment_method_field]
```

渠道表同理使用 `date_field`、`store_field`、`amount_fields`，不出现 Excel 业务列名字面量。

- [ ] **Step 6: 验证导入和提取 GREEN**

Run: `PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -p no:cacheprovider backend/tests/test_channel_extraction.py backend/tests/test_finance_extraction.py backend/tests/test_import_pipeline.py -q`

Expected: 所有来源测试通过。

Run: `rg -n 'content\.get\("日期"\)|content\.get\("金额"\)|content\.get\("付款方式"\)|profile\.(date_column|store_column|amount_columns|required_columns)' backend/app/services/{workbook_preflight.py,import_pipeline.py,extraction_engine.py,workbook_rows.py}`

Expected: 无匹配。

### Task 5: 替换和历史恢复保持绑定语义

**Files:**
- Modify: `backend/tests/test_import_versioning.py`
- Modify as needed: `backend/app/services/import_version_service.py`

**Interfaces:**
- 替换：新文件按当前配置生成自己的快照。
- 恢复：旧文件按原 `RawData` 快照提取，不读取当前配置。

- [ ] **Step 1: 写历史配置漂移回归测试**

导入使用 `支付渠道` 的财务文件，作废后把当前映射改为 `付款类型`，再恢复旧文件，断言 cash 和 sales 金额与作废前一致，并且 RawData 快照仍为 `支付渠道`。

- [ ] **Step 2: 写替换使用新绑定测试**

原文件使用“门店名”，修改配置为“门店名称”，用新列名替换文件，断言新 RawData 快照和金额正确，旧快照未改变。

- [ ] **Step 3: 运行测试并确认行为**

Run: `PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -p no:cacheprovider backend/tests/test_import_versioning.py -q`

Expected: 若 Task 4 接口完整，测试应直接通过；若失败，只修快照读取/替换调用的根因，不让恢复查询当前配置。

### Task 6: 前端来源与动态目标字段

**Files:**
- Create: `frontend/src/services/fieldMapping.ts`
- Create: `frontend/tests/fieldMapping.test.ts`
- Modify: `frontend/src/views/MappingSettings.vue`

**Interfaces:**
- Produces: `mappingSources`、`targetFieldsForSource(source)`、`normalizeTargetField(source, current)`。

- [ ] **Step 1: 写前端来源/字段矩阵失败测试**

验证来源只有 `tonglian`、`douyin`、`meituan`、`store_finance`；美团含 `marketing_fee`；财务含 `payment_method`；通联不含这两项；切换来源会规范化无效当前值。

- [ ] **Step 2: 运行测试并确认 RED**

Run: `cd frontend && node --test tests/fieldMapping.test.ts`

Expected: FAIL，共享模块不存在。

- [ ] **Step 3: 实现共享前端字段声明并接入页面**

页面移除 `cash/sales`，目标下拉由当前来源计算。监听来源变化并规范化目标字段。补充多别名/冲突说明。保存失败使用：

```ts
const detail = error.response?.data?.detail;
alert(detail || '保存字段映射失败！');
```

- [ ] **Step 4: 验证前端 GREEN**

Run: `cd frontend && node --test tests/fieldMapping.test.ts`

Expected: 所有矩阵测试通过。

Run: `cd frontend && npm test && npm run build`

Expected: 全部通过。

### Task 7: 完整回归与真实样例验收

**Files:**
- Modify as needed: `backend/tests/test_example_acceptance.py`
- Verify: 全部变更文件与设计/计划文档。

- [ ] **Step 1: 运行字段映射定向测试**

Run: `PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -p no:cacheprovider backend/tests/test_field_binding.py backend/tests/test_workbook_preflight.py backend/tests/test_channel_extraction.py backend/tests/test_finance_extraction.py backend/tests/test_import_versioning.py backend/tests/test_migrations.py -q`

Expected: 0 fail。

- [ ] **Step 2: 运行真实样例测试**

Run: `PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -p no:cacheprovider backend/tests/test_example_acceptance.py -q`

Expected: 现有通联、抖音、美团和门店财务样例全部通过，包括美团短日期兼容别名。

- [ ] **Step 3: 运行后端全量**

Run: `PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -p no:cacheprovider backend/tests -q`

Expected: 0 fail。

- [ ] **Step 4: 运行前端全量与构建**

Run: `cd frontend && npm test && npm run build`

Expected: 0 fail，类型构建成功。

- [ ] **Step 5: 运行桌面相关回归**

Run: `cd frontend/src-tauri && cargo test && cargo clippy --all-targets -- -D warnings`

Expected: 0 fail。

- [ ] **Step 6: 检查范围和迁移**

Run: `git diff --check`

Expected: 无格式错误。

Run: `rg -n "'cash'|'sales'" frontend/src/views/MappingSettings.vue frontend/src/services/fieldMapping.ts`

Expected: 字段映射来源声明中无旧来源。

Run: `git status --short && git diff --stat`

Expected: 仅字段映射全链路、迁移、测试和文档文件有变更。

## 最终人工验收

- [ ] 在字段映射页为通联门店名称增加“门店名称”。
- [ ] 上传只有“门店名称”的通联文件，预检和导入成功。
- [ ] 上传同时含“门店名”和“门店名称”的文件，看到明确冲突提示。
- [ ] 美团“验券/退款/调整时间”和样例短列名均可分别导入。
- [ ] 门店财务表付款方式改名后，配置新别名仍能正确区分现金。
- [ ] 修改配置后恢复历史文件，金额保持不变。
