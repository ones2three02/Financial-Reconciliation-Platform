# 每日对账后端正确性基础 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立可迁移、可追溯、可重算的每日对账后端，使一份门店财务表生成销售和现金，未知门店必须人工确认，并可靠区分零收入和缺少数据。

**Architecture:** 保留现有 RawData、CleanData 和 ReconciliationResult，新增批次、提取运行、来源完整性、数据质量问题与审计事件。新的服务层使用单事务和 `store_id`，旧接口在兼容期转为非破坏性行为；工作簿规则采用代码内白名单定义并把模板编码和版本持久化。

**Tech Stack:** Python 3.14、FastAPI 0.110、SQLAlchemy 2、Alembic 1.13、Pydantic 2、Pandas 2.2、OpenPyXL 3.1、Pytest 8、SQLite/MySQL 8。

## Global Constraints

- 新门店别名必须人工确认；系统建议不能自动成为有效映射。
- 不实现经办、复核双人审批，关账和重开必须留痕。
- 财务表只上传一次，同时输出 `sales` 和 `cash`。
- `present_zero` 必须有文件覆盖证据或人工确认，不能由缺少记录推断。
- 不物理覆盖、删除 ImportFile、RawData、ExtractionRun 或 AuditEvent。
- 数据库只做增量迁移；执行本地迁移前备份 `frp.db`，不执行生产迁移。
- 不新增任意公式执行能力，不新增第三方运行时依赖。
- 自动化日志不得输出姓名、电话、订单号或原始整行内容。

---

### Task 1: 建立测试基线和 Alembic 迁移骨架

**Files:**
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_migrations.py`
- Create: `backend/alembic.ini`
- Create: `backend/migrations/env.py`
- Create: `backend/migrations/script.py.mako`
- Create: `backend/migrations/versions/0001_existing_schema.py`
- Modify: `backend/tests/test_flow.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Produces: `db_session: sqlalchemy.orm.Session` Pytest fixture。
- Produces: 从空 SQLite 数据库执行 `alembic upgrade head` 的迁移入口。
- Produces: 当前数据库结构的 `0001` 基线，后续 Task 2 在其上增加 `0002`。

- [ ] **Step 1: 修正旧测试夹具并写迁移失败测试**

将公共数据库夹具移入 `backend/tests/conftest.py`，确保测试导入全部模型：

```python
@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
```

在旧现金测试行中明确加入 `"付款方式": "现金"`，使测试数据符合已经确认的业务语义。

在 `test_migrations.py` 创建临时 SQLite 文件，调用 Alembic API 升级到 `head`，断言基础表存在：

```python
def table_names(database_url: str) -> set[str]:
    engine = create_engine(database_url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()

def test_alembic_upgrade_creates_existing_schema(tmp_path):
    db_url = f"sqlite:///{tmp_path / 'migration.db'}"
    upgrade_database(db_url, "head")
    assert {"store", "import_file", "raw_data", "clean_data", "reconciliation_result"} <= table_names(db_url)
```

- [ ] **Step 2: 运行测试并确认 RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./venv/bin/pytest -p no:cacheprovider backend/tests/test_migrations.py -q
```

Expected: FAIL，原因为 Alembic 配置和 `upgrade_database` 尚不存在，而不是测试导入错误。

- [ ] **Step 3: 实现迁移测试辅助和 0001 基线**

`backend/tests/test_migrations.py` 内通过 Alembic `Config` 注入临时 URL：

```python
def upgrade_database(database_url: str, revision: str) -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, revision)
```

`0001_existing_schema.py` 必须完整创建当前七张业务表、索引、外键和唯一约束，并提供逆序 `drop_table` 的 `downgrade()`。

移除 `main.py` 中运行时 `ALTER TABLE` 的 `run_migrations()` 调用；测试仍可通过 `Base.metadata.create_all()` 创建临时表，应用数据库只由 Alembic 管理。

- [ ] **Step 4: 验证 GREEN 和现有测试基线**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./venv/bin/pytest -p no:cacheprovider backend/tests/test_migrations.py backend/tests/test_flow.py -q
```

Expected: 所有测试通过，无数据库迁移异常。

- [ ] **Step 5: 提交**

```bash
git add backend/alembic.ini backend/migrations backend/tests/conftest.py backend/tests/test_migrations.py backend/tests/test_flow.py backend/app/main.py
git commit -m "build: 建立 Alembic 迁移和测试基线"
```

---

### Task 2: 新增批次、提取、完整性和审计模型

**Files:**
- Create: `backend/app/models/batch.py`
- Create: `backend/app/models/extraction.py`
- Create: `backend/app/models/coverage.py`
- Create: `backend/app/models/quality_issue.py`
- Create: `backend/app/models/audit.py`
- Create: `backend/app/models/store_source_requirement.py`
- Create: `backend/migrations/versions/0002_reconciliation_foundation.py`
- Create: `backend/tests/test_foundation_models.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/models/import_file.py`
- Modify: `backend/app/models/clean_data.py`
- Modify: `backend/app/models/reconciliation.py`
- Modify: `backend/app/models/store.py`

**Interfaces:**
- Produces: `ReconciliationBatch`、`ExtractionProfile`、`ExtractionRun`、`SourceCoverage`、`DataQualityIssue`、`AuditEvent`、`StoreSourceRequirement`。
- Produces: `ImportFile.content_hash`、`ImportFile.batch_id`、`CleanData.store_id`、`ReconciliationResult.batch_id/store_id`。
- Consumes: Task 1 的 Alembic 基线。

- [ ] **Step 1: 写模型约束失败测试**

测试至少覆盖：

```python
def test_one_batch_per_business_date(db_session):
    db_session.add(ReconciliationBatch(business_date=date(2026, 7, 10)))
    db_session.commit()
    db_session.add(ReconciliationBatch(business_date=date(2026, 7, 10)))
    with pytest.raises(IntegrityError):
        db_session.commit()

def test_source_coverage_unique_per_batch_store_source(db_session, batch, store):
    first = SourceCoverage(batch_id=batch.id, business_date=batch.business_date, store_id=store.id, source_code="cash", status="present_zero", evidence_type="file_scope")
    duplicate = SourceCoverage(batch_id=batch.id, business_date=batch.business_date, store_id=store.id, source_code="cash", status="missing")
    db_session.add_all([first, duplicate])
    with pytest.raises(IntegrityError):
        db_session.commit()
```

同时断言 AuditEvent 没有级联删除关系，StoreAlias 包含 `source_code`、`confirmed_by` 和 `confirmed_at`。

- [ ] **Step 2: 运行测试并确认 RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./venv/bin/pytest -p no:cacheprovider backend/tests/test_foundation_models.py -q
```

Expected: FAIL，缺少新模型或字段。

- [ ] **Step 3: 实现 SQLAlchemy 模型和 0002 增量迁移**

所有状态使用受控字符串常量，金额使用 `Numeric(14, 2)`。关键唯一约束：

```python
UniqueConstraint("business_date", name="uq_reconciliation_batch_business_date")
UniqueConstraint("batch_id", "store_id", "source_code", name="uq_source_coverage_scope")
UniqueConstraint("batch_id", "store_id", name="uq_reconciliation_result_batch_store")
UniqueConstraint("source_code", "alias_name", name="uq_store_alias_source_name")
```

迁移只新增结构。旧 `store_alias` 唯一约束通过 SQLite/MySQL 兼容的 batch operation 转换；现有映射保留记录但置为 `pending`，因为当前数据库无法证明其经过人工确认。

- [ ] **Step 4: 验证模型和迁移升级/降级**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./venv/bin/pytest -p no:cacheprovider backend/tests/test_foundation_models.py backend/tests/test_migrations.py -q
```

Expected: PASS；`upgrade head → downgrade 0001 → upgrade head` 均成功。

- [ ] **Step 5: 提交**

```bash
git add backend/app/models backend/migrations/versions/0002_reconciliation_foundation.py backend/tests/test_foundation_models.py
git commit -m "feat: 新增每日对账基础数据模型"
```

---

### Task 3: 实现白名单提取模板和工作簿预检

**Files:**
- Create: `backend/app/domain/extraction_profiles.py`
- Create: `backend/app/services/workbook_preflight.py`
- Create: `backend/app/schemas/preflight.py`
- Create: `backend/tests/test_workbook_preflight.py`

**Interfaces:**
- Produces: `get_profile(profile_code: str) -> ProfileDefinition`。
- Produces: `preflight_workbook(content: bytes, profile_code: str, business_date: date, store_id: int | None) -> PreflightResult`。
- Produces: 模板编码 `store_finance_v1`、`douyin_v1`、`meituan_v1`、`tonglian_v1`。
- Produces: `TemplateMismatchError(ValueError)`，只携带模板、工作表和缺失字段，不携带数据行。

- [ ] **Step 1: 用脱敏工作簿写预检失败测试**

测试内存创建四种工作簿，禁止使用真实姓名、电话和订单号。核心断言：

```python
def test_finance_profile_requires_exact_sheet_and_store(finance_bytes):
    result = preflight_workbook(finance_bytes, "store_finance_v1", date(2026, 7, 10), store_id=10)
    assert result.sheet_name == "收入流水表"
    assert result.output_sources == ["sales", "cash"]

def test_meituan_profile_rejects_missing_marketing_column(meituan_without_marketing):
    with pytest.raises(TemplateMismatchError, match="商家营销费用"):
        preflight_workbook(meituan_without_marketing, "meituan_v1", date(2026, 7, 10), None)
```

- [ ] **Step 2: 运行测试并确认 RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./venv/bin/pytest -p no:cacheprovider backend/tests/test_workbook_preflight.py -q
```

Expected: FAIL，预检模块不存在。

- [ ] **Step 3: 实现只读预检和资源限制**

`ProfileDefinition` 明确声明表名、表头、字段和提取器，不接受数据库中的可执行字符串：

```python
@dataclass(frozen=True)
class ProfileDefinition:
    code: str
    version: int
    sheet_names: tuple[str, ...]
    required_columns: tuple[str, ...]
    extractor: Literal["sum_column", "sum_filtered_column", "sum_columns"]
    date_column: str
    store_column: str | None
    amount_columns: tuple[str, ...]
    output_sources: tuple[str, ...]
    requires_store_id: bool = False

ProfileDefinition(
    code="meituan_v1",
    version=1,
    sheet_names=("收益明细表",),
    required_columns=("验券/退款/", "消费门店", "总收入（元）", "商家营销费用（元）"),
    extractor="sum_columns",
    amount_columns=("总收入（元）", "商家营销费用（元）"),
    output_sources=("meituan",),
)
```

预检限制文件大小、工作表数量、行数和列数；错误信息只包含文件元数据、工作表和表头，不包含原始数据行。

- [ ] **Step 4: 验证 GREEN**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./venv/bin/pytest -p no:cacheprovider backend/tests/test_workbook_preflight.py -q
```

Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add backend/app/domain backend/app/services/workbook_preflight.py backend/app/schemas/preflight.py backend/tests/test_workbook_preflight.py
git commit -m "feat: 新增工作簿提取模板和预检"
```

---

### Task 4: 实现批次、哈希去重和原始数据原子导入

**Files:**
- Create: `backend/app/services/batch_service.py`
- Create: `backend/app/services/import_pipeline.py`
- Create: `backend/app/schemas/batch.py`
- Create: `backend/tests/test_import_pipeline.py`
- Modify: `backend/app/services/parser.py`

**Interfaces:**
- Produces: `get_or_create_batch(db: Session, business_date: date, actor: str) -> ReconciliationBatch`。
- Produces: `calculate_content_hash(content: bytes) -> str`。
- Produces: `import_workbook(db: Session, command: ImportWorkbookCommand) -> ImportOutcome`。
- Consumes: Task 3 的 `PreflightResult`。

```python
@dataclass(frozen=True)
class ImportWorkbookCommand:
    batch_id: int
    filename: str
    content: bytes
    profile_code: str
    store_id: int | None
    actor: str

@dataclass(frozen=True)
class ImportOutcome:
    status: Literal["imported", "duplicate", "attention_required"]
    import_file_id: int
    extraction_run_id: int | None
```

- [ ] **Step 1: 写重复和事务失败测试**

```python
def test_same_hash_in_same_batch_is_duplicate(db_session, finance_command):
    first = import_workbook(db_session, finance_command)
    second = import_workbook(db_session, finance_command)
    assert second.status == "duplicate"
    assert second.import_file_id == first.import_file_id

def test_same_filename_with_different_content_is_preserved(db_session, finance_command):
    first = import_workbook(db_session, finance_command)
    second = import_workbook(db_session, replace(finance_command, content=changed_bytes))
    assert first.import_file_id != second.import_file_id
    assert count_import_files(db_session) == 2
```

增加故障注入测试：RawData 写入中途抛错后，ImportFile、RawData 和 ExtractionRun 均不留下半成品。

- [ ] **Step 2: 运行测试并确认 RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./venv/bin/pytest -p no:cacheprovider backend/tests/test_import_pipeline.py -q
```

Expected: FAIL，新导入管道不存在。

- [ ] **Step 3: 实现单事务导入管道**

服务只在最外层控制事务，内部函数只使用 `flush()`：

```python
with db.begin_nested():
    import_file = register_import_file(...)
    raw_rows = persist_raw_rows(...)
    extraction_run = create_extraction_run(...)
```

删除新管道中的中间 `commit()`。旧 `parse_excel_file()` 暂时作为兼容适配器，但不得被新批次 API 调用。

- [ ] **Step 4: 验证 GREEN 和原子性**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./venv/bin/pytest -p no:cacheprovider backend/tests/test_import_pipeline.py -q
```

Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/batch_service.py backend/app/services/import_pipeline.py backend/app/services/parser.py backend/app/schemas/batch.py backend/tests/test_import_pipeline.py
git commit -m "feat: 新增批次化原子导入和文件去重"
```

---

### Task 5: 实现财务表多来源提取和零收入证据

**Files:**
- Create: `backend/app/services/extraction_engine.py`
- Create: `backend/app/services/coverage_service.py`
- Create: `backend/tests/test_finance_extraction.py`
- Modify: `backend/app/services/import_pipeline.py`

**Interfaces:**
- Produces: `extract_current_batch_rows(db: Session, extraction_run_id: int) -> ExtractionSummary`。
- Produces: `upsert_coverage(..., status: str, evidence_type: str, amount: Decimal) -> SourceCoverage`。

```python
@dataclass(frozen=True)
class ExtractionSummary:
    extraction_run_id: int
    source_amounts: dict[str, Decimal]
    clean_row_count: int
    issue_count: int
```

- [ ] **Step 1: 写一次导入产生 sales/cash 的失败测试**

```python
def test_finance_file_generates_sales_and_cash(db_session, finance_bytes, batch, minyuan_store):
    outcome = import_finance(...)
    assert source_amount(db_session, batch.id, minyuan_store.id, "sales") == Decimal("120.00")
    assert source_amount(db_session, batch.id, minyuan_store.id, "cash") == Decimal("20.00")

def test_finance_without_cash_creates_present_zero(db_session, no_cash_finance_bytes, batch, minyuan_store):
    import_finance(...)
    coverage = get_coverage(..., source_code="cash")
    assert coverage.status == "present_zero"
    assert coverage.evidence_type == "file_scope"
    assert coverage.amount == Decimal("0.00")
```

- [ ] **Step 2: 运行测试并确认 RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./venv/bin/pytest -p no:cacheprovider backend/tests/test_finance_extraction.py -q
```

Expected: FAIL，尚无多来源提取。

- [ ] **Step 3: 实现按批次日期提取**

RawData 保存月度文件全部行；CleanData 只生成 `trade_date == batch.business_date` 的当前有效行。现金只生成真实现金明细，零现金只更新 SourceCoverage，不创建金额为零的伪明细。

金额始终使用 Decimal：

```python
sales_amount = sum((row.amount for row in sales_rows), Decimal("0.00"))
cash_rows = [row for row in sales_rows if row.payment_method == "现金"]
cash_amount = sum((row.amount for row in cash_rows), Decimal("0.00"))
```

- [ ] **Step 4: 验证 GREEN**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./venv/bin/pytest -p no:cacheprovider backend/tests/test_finance_extraction.py -q
```

Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/extraction_engine.py backend/app/services/coverage_service.py backend/app/services/import_pipeline.py backend/tests/test_finance_extraction.py
git commit -m "feat: 财务表一次导入生成销售和现金"
```

---

### Task 6: 实现来源级人工门店确认和数据质量门禁

**Files:**
- Create: `backend/app/services/store_resolution.py`
- Create: `backend/app/services/quality_service.py`
- Create: `backend/tests/test_store_resolution.py`
- Modify: `backend/app/services/extraction_engine.py`
- Modify: `backend/app/crud/store.py`
- Modify: `backend/app/schemas/store.py`
- Modify: `backend/app/api/stores.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Produces: `resolve_store(db, source_code, raw_name) -> StoreResolution`。
- Produces: `confirm_alias(db, alias_id, store_id, actor) -> StoreAlias`。
- Produces: `reprocess_affected_runs(db, alias_id) -> list[int]`。

```python
@dataclass(frozen=True)
class StoreResolution:
    status: Literal["resolved", "pending"]
    store_id: int | None
    alias_id: int | None
    suggestions: tuple[int, ...]
```

- [ ] **Step 1: 写人工确认失败测试**

```python
def test_unknown_alias_does_not_bind_from_similarity(db_session, minyuan_store):
    resolution = resolve_store(db_session, "meituan", "武汉 : 山道健身游泳舞蹈(曙光店)")
    assert resolution.status == "pending"
    assert resolution.store_id is None
    assert open_issue_count(db_session, "unknown_store") == 1

def test_confirmation_is_source_specific_and_reprocesses(db_session, pending_alias, minyuan_store):
    confirm_alias(db_session, pending_alias.id, minyuan_store.id, actor="admin")
    assert resolve_store(db_session, "meituan", pending_alias.alias_name).store_id == minyuan_store.id
    assert resolve_store(db_session, "douyin", pending_alias.alias_name).status == "pending"
```

- [ ] **Step 2: 运行测试并确认 RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./venv/bin/pytest -p no:cacheprovider backend/tests/test_store_resolution.py -q
```

Expected: FAIL，旧逻辑没有来源维度或确认审计。

- [ ] **Step 3: 实现精确匹配和确认服务**

匹配只允许：

```python
if raw_name == store.name:
    return resolved(store.id, "exact_standard_name")
if confirmed_alias := find_confirmed_alias(source_code, raw_name):
    return resolved(confirmed_alias.store_id, "confirmed_alias")
return pending_with_suggestions(...)
```

移除 `main.py` 中硬编码别名自动播种。确认操作更新确认人和时间、写 AuditEvent、关闭 DataQualityIssue，并重处理受影响运行。

- [ ] **Step 4: 验证 GREEN**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./venv/bin/pytest -p no:cacheprovider backend/tests/test_store_resolution.py -q
```

Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/store_resolution.py backend/app/services/quality_service.py backend/app/services/extraction_engine.py backend/app/crud/store.py backend/app/schemas/store.py backend/app/api/stores.py backend/app/main.py backend/tests/test_store_resolution.py
git commit -m "feat: 新增门店别名人工确认门禁"
```

---

### Task 7: 实现抖音、美团、通联提取规则

**Files:**
- Create: `backend/tests/test_channel_extraction.py`
- Modify: `backend/app/services/extraction_engine.py`
- Modify: `backend/app/domain/extraction_profiles.py`

**Interfaces:**
- Consumes: Task 3 的模板和 Task 6 的 `resolve_store()`。
- Produces: 三类渠道的当前批次 CleanData、SourceCoverage 和 DataQualityIssue。

- [ ] **Step 1: 写三个来源失败测试**

```python
def test_meituan_adds_signed_marketing_amount(...):
    assert extracted_amount == Decimal("342.40")  # 377.40 + (-35.00)

def test_douyin_uses_redemption_date_store_and_order_receipt(...):
    assert extracted_amount == Decimal("296.00")

def test_tonglian_sums_multiple_rows_for_confirmed_aliases(...):
    assert extracted_amount == Decimal("20480.00")
```

同时验证未知别名不会进入有效金额，外部来源没有记录时仍为 `missing`。

- [ ] **Step 2: 运行测试并确认 RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./venv/bin/pytest -p no:cacheprovider backend/tests/test_channel_extraction.py -q
```

Expected: FAIL，渠道提取器尚未实现。

- [ ] **Step 3: 实现白名单渠道提取器**

每个提取器只读取模板声明字段，按批次日期过滤，金额保留原始正负号。抖音不增加未确认的撤销业务规则；如果出现未定义状态，只创建 DataQualityIssue。

- [ ] **Step 4: 验证 GREEN**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./venv/bin/pytest -p no:cacheprovider backend/tests/test_channel_extraction.py -q
```

Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/extraction_engine.py backend/app/domain/extraction_profiles.py backend/tests/test_channel_extraction.py
git commit -m "feat: 实现三类外部渠道提取规则"
```

---

### Task 8: 实现完整性对账、人工零收入和单人关账

**Files:**
- Create: `backend/app/services/reconciliation_service.py`
- Create: `backend/app/services/closing_service.py`
- Create: `backend/tests/test_reconciliation_batch.py`
- Modify: `backend/app/services/reconciler.py`
- Modify: `backend/app/schemas/reconciliation.py`
- Modify: `backend/app/api/reconciliation.py`

**Interfaces:**
- Produces: `reconcile_batch(db, batch_id) -> list[ReconciliationResult]`。
- Produces: `confirm_zero(db, batch_id, store_id, source_code, actor) -> SourceCoverage`。
- Produces: `close_batch(db, batch_id, actor) -> ReconciliationBatch`。
- Produces: `reopen_batch(db, batch_id, actor, reason) -> ReconciliationBatch`。

- [ ] **Step 1: 写完整性和关账失败测试**

```python
def test_zero_and_missing_have_different_reconciliation_status(...):
    assert reconcile_with_present_zero().status == "consistent"
    assert reconcile_with_missing_source().status == "incomplete"

def test_close_rejects_open_quality_issue(...):
    with pytest.raises(BatchNotClosableError, match="待确认门店"):
        close_batch(db, batch.id, actor="admin")

def test_reopen_requires_reason_and_writes_audit(...):
    with pytest.raises(ValueError):
        reopen_batch(db, batch.id, actor="admin", reason="")
```

- [ ] **Step 2: 运行测试并确认 RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./venv/bin/pytest -p no:cacheprovider backend/tests/test_reconciliation_batch.py -q
```

Expected: FAIL，新对账和关账服务不存在。

- [ ] **Step 3: 实现完整性优先的对账状态机**

先判断 SourceCoverage，再计算金额：

```python
if has_blocking_coverage or has_open_quality_issue:
    status = "incomplete"
else:
    difference = expected - actual
    status = "consistent" if difference == Decimal("0.00") else "discrepancy"
```

人工零收入写 `evidence_type="manual_zero_confirmation"` 和 AuditEvent。关账只允许 `ready_to_close`；重开原因去除首尾空白后不能为空。

- [ ] **Step 4: 验证 GREEN**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./venv/bin/pytest -p no:cacheprovider backend/tests/test_reconciliation_batch.py -q
```

Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/reconciliation_service.py backend/app/services/closing_service.py backend/app/services/reconciler.py backend/app/schemas/reconciliation.py backend/app/api/reconciliation.py backend/tests/test_reconciliation_batch.py
git commit -m "feat: 新增批次完整性对账和单人关账"
```

---

### Task 9: 暴露批次 API 并禁用破坏性旧行为

**Files:**
- Create: `backend/app/api/batches.py`
- Create: `backend/app/api/preflight.py`
- Create: `backend/app/schemas/import_command.py`
- Create: `backend/tests/test_api_contracts.py`
- Modify: `backend/app/api/files.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Produces: `POST /api/v1/batches`、`GET /api/v1/batches/{id}`。
- Produces: `POST /api/v1/files/preflight`、`POST /api/v1/files/import`。
- Produces: `POST /api/v1/batches/{id}/confirm-zero`、`close`、`reopen`、`reconcile`。
- Produces: `POST /api/v1/stores/aliases/{id}/confirm`。

- [ ] **Step 1: 写路由契约失败测试**

不新增 HTTP 测试依赖，直接调用路由函数并验证 Pydantic 输入输出及 HTTPException：

```python
def test_closed_batch_rejects_file_import(db_session, closed_batch, upload_file):
    with pytest.raises(HTTPException) as exc:
        import_file_route(...)
    assert exc.value.status_code == 409
```

验证旧 `DELETE /files/{id}` 不再物理删除记录，而是返回 409 和替代操作说明；旧同名上传不再自动覆盖。

- [ ] **Step 2: 运行测试并确认 RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./venv/bin/pytest -p no:cacheprovider backend/tests/test_api_contracts.py -q
```

Expected: FAIL，新路由不存在或旧路由仍执行删除。

- [ ] **Step 3: 实现薄路由和兼容错误**

路由只负责校验、调用服务和转换异常，不写金额、门店匹配或事务规则。旧破坏性端点返回明确的 409，不再删除已有数据。

- [ ] **Step 4: 验证 GREEN**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./venv/bin/pytest -p no:cacheprovider backend/tests/test_api_contracts.py -q
```

Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add backend/app/api backend/app/schemas/import_command.py backend/app/main.py backend/tests/test_api_contracts.py
git commit -m "feat: 暴露每日批次 API 并禁用物理删除"
```

---

### Task 10: 民院店真实样例验收、迁移备份和后端全量验证

**Files:**
- Create: `backend/tests/test_example_acceptance.py`
- Create: `backend/scripts/backup_sqlite.py`
- Modify: `README.md`
- Modify: `docs/database/migration.md`

**Interfaces:**
- Produces: 只输出汇总金额和行数的真实样例验收测试。
- Produces: `python backend/scripts/backup_sqlite.py frp.db` 本地备份入口。

- [ ] **Step 1: 写真实样例验收测试并确认 RED**

测试只断言汇总，不打印原始行：

```python
def test_minyuan_2026_07_10_reconciles_to_zero(example_paths, db_session):
    # 创建批次，导入四份样例，逐项人工确认四个来源别名后重算
    result = get_result(db_session, date(2026, 7, 10), "民院店")
    assert result.tonglian_amount == Decimal("20480.00")
    assert result.meituan_amount == Decimal("9.90")
    assert result.douyin_amount == Decimal("296.00")
    assert result.sales_amount == Decimal("20785.90")
    assert result.cash_amount == Decimal("0.00")
    assert result.difference == Decimal("0.00")
```

首次运行应因尚未确认美团等别名而得到 `incomplete`，测试再通过显式 `confirm_alias()` 完成确认并重算。

- [ ] **Step 2: 运行验收测试并确认 RED/业务门禁**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./venv/bin/pytest -p no:cacheprovider backend/tests/test_example_acceptance.py -q
```

Expected: 首次实现前 FAIL；实现后测试内部先验证待映射状态，再验证人工确认后的零差异。

- [ ] **Step 3: 实现备份脚本和迁移文档**

备份脚本使用 `sqlite3.Connection.backup()` 生成带 UTC 时间戳的副本，不修改源数据库。文档写明现有本地数据库执行顺序：

```text
1. backup_sqlite.py frp.db
2. alembic stamp 0001_existing_schema
3. alembic upgrade head
4. 验证 alembic current
```

不得自动对生产数据库执行上述命令。

- [ ] **Step 4: 运行完整后端验证**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./venv/bin/pytest -p no:cacheprovider backend/tests -q
```

Expected: 0 failed。

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 ./venv/bin/python -m compileall -q backend/app backend/tests backend/scripts
```

Expected: exit 0。

Run:

```bash
./venv/bin/pip check
```

Expected: `No broken requirements found.`

- [ ] **Step 5: 备份并迁移本地开发数据库**

仅在前述测试全部通过后执行：

```bash
./venv/bin/python backend/scripts/backup_sqlite.py frp.db
./venv/bin/alembic -c backend/alembic.ini stamp 0001_existing_schema
./venv/bin/alembic -c backend/alembic.ini upgrade head
./venv/bin/alembic -c backend/alembic.ini current
```

Expected: 备份文件存在，当前版本为 `0002_reconciliation_foundation (head)`。若任一步失败，停止并使用备份恢复，不继续运行应用。

- [ ] **Step 6: 提交**

```bash
git add backend/tests/test_example_acceptance.py backend/scripts/backup_sqlite.py README.md docs/database/migration.md
git commit -m "test: 增加民院店真实样例验收"
```

---

## 计划自审清单

- 设计规范的批次、哈希、模板、多来源、人工映射、完整性、对账、关账、审计和验收均有对应任务。
- 所有生产代码任务都有先失败、再实现、再回归的测试步骤。
- 新旧模型通过 0001/0002 两阶段迁移衔接，不在应用启动时执行 DDL。
- 第一轮没有新增前端页面、正式认证、通知或任意公式语言。
- 第一轮没有物理删除原始导入数据，也没有生产迁移步骤。
