# Human Error Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为确认零、历史文件、整批重置、门店别名、主数据和差异处理建立分级确认、业务级撤销及完整审计，防止用户误操作造成不可恢复或历史数据重新参与计算。

**Architecture:** 复用现有 `is_current`、RawData、SourceCoverage 和 AuditEvent，不新增数据库表。撤销零直接恢复覆盖为缺失；文件与批次恢复从 RawData 创建全新 ExtractionRun 重提；整批重置在审计 JSON 中保存小型业务快照，并用状态门禁保证只能安全恢复一次。

**Tech Stack:** FastAPI、SQLAlchemy 2、Pydantic v2、pytest、Vue 3、TypeScript、Axios、现有 shadcn-vue 风格组件。

## Global Constraints

- 不增加经办/复核双人审批，二次确认由同一登录用户完成。
- 不物理删除导入、原始、标准、门店或映射数据。
- 不新增第三方依赖，不新增数据库表或 Alembic 迁移。
- 已关账批次的撤销和恢复必须先重开。
- actor 一律取服务端登录会话，原因长度为 1–500 字。
- 任意恢复失败必须整体回滚，恢复前当前数据继续有效。
- 前端显示后端中文错误，不吞掉失败。

---

### Task 1: 阻止历史文件和历史运行被重新提取

**Files:**
- Modify: `backend/app/services/extraction_engine.py`
- Modify: `backend/app/services/store_resolution.py`
- Test: `backend/tests/test_channel_extraction.py`

**Interfaces:**
- Produces: `HistoricalExtractionError(ValueError)`；`extract_current_batch_rows(db, extraction_run_id)` 仅接受当前文件和当前运行。
- Produces: `_affected_run_ids(db, alias) -> list[int]` 只返回当前文件的当前运行。

- [ ] **Step 1: Write failing tests**

```python
def test_historical_run_cannot_be_extracted(db_session):
    outcome = import_channel(db_session, batch.id, "meituan_v1", content)
    run = db_session.get(ExtractionRun, outcome.extraction_run_id)
    run.is_current = False
    db_session.commit()
    with pytest.raises(HistoricalExtractionError):
        extract_current_batch_rows(db_session, run.id)

def test_alias_rebind_does_not_reprocess_historical_file(db_session, monkeypatch):
    imported_file.is_current = False
    run.is_current = False
    confirm_alias(db_session, alias_id=alias.id, store_id=new_store.id, actor="admin", reason="修正绑定")
    assert called_run_ids == []
```

- [ ] **Step 2: Run tests and verify RED**

Run: `'/Users/croodslee/Vibe Coding/Financial-Reconciliation-Platform/venv/bin/python' -m pytest backend/tests/test_channel_extraction.py -q`
Expected: FAIL because historical runs are still accepted.

- [ ] **Step 3: Add current-version gates**

```python
class HistoricalExtractionError(ValueError):
    """历史文件或历史提取运行不能直接重新提取。"""

if not import_file.is_current or not extraction_run.is_current:
    raise HistoricalExtractionError("历史文件或历史提取运行不能重新进入当前计算")
```

Update `_affected_run_ids` by joining `ExtractionRun` and `ImportFile`, filtering both `is_current` columns to `True`.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `'/Users/croodslee/Vibe Coding/Financial-Reconciliation-Platform/venv/bin/python' -m pytest backend/tests/test_channel_extraction.py backend/tests/test_store_resolution.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/extraction_engine.py backend/app/services/store_resolution.py backend/tests/test_channel_extraction.py
git commit -m "fix: 阻止历史导入数据被重新提取"
```

### Task 2: 撤销人工确认零收入

**Files:**
- Modify: `backend/app/schemas/batch.py`
- Modify: `backend/app/services/reconciliation_service.py`
- Modify: `backend/app/api/batches.py`
- Test: `backend/tests/test_reconciliation_batch.py`
- Test: `backend/tests/test_api_contracts.py`

**Interfaces:**
- Produces: `RevokeZeroRequest(store_id: int, source_code: str, reason: str)`。
- Produces: `revoke_zero(db, *, batch_id, store_id, source_code, reason, actor) -> SourceCoverage`。
- Produces: `POST /api/v1/batches/{batch_id}/revoke-zero`。

- [ ] **Step 1: Write failing service tests**

```python
def test_manual_zero_can_be_revoked_to_missing(db_session):
    confirm_zero(db_session, batch_id=batch.id, store_id=store.id, source_code="tonglian", actor="finance")
    revoke_zero(db_session, batch_id=batch.id, store_id=store.id, source_code="tonglian", reason="误确认", actor="finance")
    assert coverage.status == "missing"
    assert result.status == "incomplete"
    assert audit.event_type == "source_zero_confirmation_revoked"

def test_file_scope_zero_cannot_be_revoked(db_session):
    coverage.evidence_type = "file_scope"
    with pytest.raises(ValueError, match="只能撤销人工确认"):
        revoke_zero(db_session, batch_id=batch.id, store_id=store.id, source_code="cash", reason="误操作", actor="finance")
```

Also cover closed batch, blank reason and session actor through the API route.

- [ ] **Step 2: Run tests and verify RED**

Run: `'/Users/croodslee/Vibe Coding/Financial-Reconciliation-Platform/venv/bin/python' -m pytest backend/tests/test_reconciliation_batch.py backend/tests/test_api_contracts.py -q`
Expected: FAIL because revoke API and service do not exist.

- [ ] **Step 3: Implement revoke service and route**

```python
def revoke_zero(db: Session, *, batch_id: int, store_id: int, source_code: str, reason: str, actor: str) -> SourceCoverage:
    # require present_zero + manual_zero_confirmation + open batch
    # set missing fields, reconcile, add audit, flush
```

The API commits once; errors map to 400/404/409 with Chinese detail.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `'/Users/croodslee/Vibe Coding/Financial-Reconciliation-Platform/venv/bin/python' -m pytest backend/tests/test_reconciliation_batch.py backend/tests/test_api_contracts.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/batch.py backend/app/services/reconciliation_service.py backend/app/api/batches.py backend/tests/test_reconciliation_batch.py backend/tests/test_api_contracts.py
git commit -m "feat: 支持撤销人工确认零收入"
```

### Task 3: 确认零二次确认和撤销界面

**Files:**
- Modify: `frontend/src/services/api.ts`
- Modify: `frontend/src/views/ReconciliationList.vue`

**Interfaces:**
- Consumes: `POST /batches/{id}/revoke-zero`。
- Produces: `api.revokeZero(batchId, storeId, sourceCode, reason)`。

- [ ] **Step 1: Add API method and modal state**

```ts
revokeZero: (batchId: number, storeId: number, sourceCode: SourceCode, reason: string) =>
  client.post(`/batches/${batchId}/revoke-zero`, { store_id: storeId, source_code: sourceCode, reason })
```

Add `zeroConfirmation`, `zeroRevocation`, `zeroRevokeReason` refs. A click on a missing cell opens the confirmation modal rather than calling the API.

- [ ] **Step 2: Render exact business scope**

The confirmation modal renders business date, store name, source label and “缺失不等于零”. The grid renders “撤销确认” only when `status === 'present_zero' && evidence_type === 'manual_zero_confirmation'`.

- [ ] **Step 3: Wire submit and refresh**

Confirm submits `confirmZero`; revoke requires trimmed reason and submits `revokeZero`; both reload batch detail and display a Chinese success/error notice.

- [ ] **Step 4: Build**

Run: `cd frontend && npm run build`
Expected: TypeScript and Vite build PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/services/api.ts frontend/src/views/ReconciliationList.vue
git commit -m "feat: 增加确认零二次确认和撤销入口"
```

### Task 4: 恢复历史导入文件

**Files:**
- Modify: `backend/app/services/import_version_service.py`
- Modify: `backend/app/schemas/import_command.py`
- Modify: `backend/app/api/files.py`
- Test: `backend/tests/test_import_versioning.py`
- Test: `backend/tests/test_api_contracts.py`

**Interfaces:**
- Produces: `RestoreImportRequest(reason: str)`。
- Produces: `restore_import_file(db, *, file_id: int, reason: str, actor: str) -> ImportOutcome`。
- Produces: `POST /api/v1/files/{file_id}/restore`。
- Produces helpers: `_chain_contains(db, current_file, target_file_id) -> bool`、`_locked_historical_file(db, file_id) -> tuple[ImportFile, ReconciliationBatch]`、`_record_file_restored(db, target, run, reason, actor) -> None`。

- [ ] **Step 1: Write failing restore tests**

```python
def test_invalidated_file_can_be_restored_from_raw_data(db_session):
    invalidate_import_file(db_session, file_id=file.id, reason="测试作废", actor="finance")
    outcome = restore_import_file(db_session, file_id=file.id, reason="误作废", actor="finance")
    assert file.is_current is True
    assert outcome.extraction_run_id != old_run.id
    assert current_amount(db_session, batch.id, store.id, "sales") == Decimal("100.00")

def test_restoring_old_version_retires_current_descendant(db_session):
    replacement = replace_import_file(db_session, file_id=original.id, filename="正确.xlsx", content=new_content, reason="测试替换", actor="finance")
    restore_import_file(db_session, file_id=original.id, reason="恢复原版", actor="finance")
    assert original.is_current is True
    assert replacement_file.is_current is False
```

Also test duplicate independent file, closed batch, already-current target and extraction failure rollback.

- [ ] **Step 2: Run tests and verify RED**

Run: `'/Users/croodslee/Vibe Coding/Financial-Reconciliation-Platform/venv/bin/python' -m pytest backend/tests/test_import_versioning.py backend/tests/test_api_contracts.py -q`
Expected: FAIL because restore operation does not exist.

- [ ] **Step 3: Implement chain restore**

Add helpers with exact signatures:

```python
def _current_descendants(db: Session, target: ImportFile) -> list[ImportFile]:
    current_files = db.query(ImportFile).filter_by(batch_id=target.batch_id, is_current=True).all()
    return [row for row in current_files if _chain_contains(db, row, target.id)]

def _new_extraction_run(db: Session, import_file: ImportFile) -> ExtractionRun:
    raw_count = db.query(RawData).filter_by(import_file_id=import_file.id).count()
    run = ExtractionRun(import_file_id=import_file.id, profile_code=import_file.profile_code, profile_version=import_file.profile_version, status="pending", raw_row_count=raw_count, is_current=True)
    db.add(run)
    db.flush()
    return run

def restore_import_file(db: Session, *, file_id: int, reason: str, actor: str) -> ImportOutcome:
    target, batch = _locked_historical_file(db, file_id)
    old_scopes = set().union(*(_file_scopes(db, row) for row in _current_descendants(db, target)))
    for row in _current_descendants(db, target):
        _retire_file(db, row, actor)
    target.is_current = True
    run = _new_extraction_run(db, target)
    summary = extract_current_batch_rows(db, run.id)
    _refresh_scopes(db, batch, old_scopes | _file_scopes(db, target))
    reconcile_batch(db, batch.id)
    _record_file_restored(db, target, run, reason, actor)
    return ImportOutcome("attention_required" if summary.issue_count else "imported", target.id, run.id)
```

The service locks batch then file, retires current descendants, reactivates target, creates a new run from RawData count, extracts, refreshes union scopes, reconciles and writes `file_restored` in one transaction.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `'/Users/croodslee/Vibe Coding/Financial-Reconciliation-Platform/venv/bin/python' -m pytest backend/tests/test_import_versioning.py backend/tests/test_api_contracts.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/import_version_service.py backend/app/schemas/import_command.py backend/app/api/files.py backend/tests/test_import_versioning.py backend/tests/test_api_contracts.py
git commit -m "feat: 支持恢复历史导入文件"
```

### Task 5: 保存重置快照并恢复上一次重置

**Files:**
- Modify: `backend/app/schemas/import_command.py`
- Modify: `backend/app/schemas/batch.py`
- Modify: `backend/app/services/import_version_service.py`
- Modify: `backend/app/api/batches.py`
- Test: `backend/tests/test_import_versioning.py`
- Test: `backend/tests/test_api_contracts.py`

**Interfaces:**
- Changes: `ResetBatchCurrentDataRequest` adds `risk_acknowledged: bool` and rejects false。
- Produces: `RestoreLastResetRequest(reason, confirmation_date, risk_acknowledged)`。
- Produces: `restore_last_reset(db, *, batch_id, reason, confirmation_date, risk_acknowledged, actor) -> ReconciliationBatch`。
- Produces: `POST /api/v1/batches/{batch_id}/restore-last-reset`。
- Changes: `BatchDetailRead` adds `can_restore_last_reset: bool` and `last_reset_event_id: int | None`。
- Produces helpers: `_locked_open_batch`、`_latest_unrestored_reset_event`、`_validate_reset_restore_state`、`_restore_snapshot_file`、`_restore_manual_zero`、`_record_reset_restored`，全部位于 `import_version_service.py`，不对 API 层暴露。

- [ ] **Step 1: Write failing snapshot and restore tests**

```python
def test_reset_audit_contains_small_snapshot(db_session):
    reset_batch_current_data(db_session, batch_id=batch.id, reason="测试重置", confirmation_date=batch.business_date, risk_acknowledged=True, actor="finance")
    assert audit.event_data["current_file_ids"] == [file.id]
    assert audit.event_data["manual_zero_scopes"] == [{"store_id": store.id, "source_code": "tonglian"}]
    assert "clean_data_ids" not in audit.event_data

def test_last_reset_can_be_restored_once(db_session):
    reset_batch_current_data(db_session, batch_id=batch.id, reason="测试重置", confirmation_date=batch.business_date, risk_acknowledged=True, actor="finance")
    restored = restore_last_reset(db_session, batch_id=batch.id, reason="误重置", confirmation_date=batch.business_date, risk_acknowledged=True, actor="finance")
    assert current_files == [file]
    assert manual_zero.status == "present_zero"
    with pytest.raises(ImportVersionConflictError, match="已经恢复"):
        restore_last_reset(db_session, batch_id=batch.id, reason="重复恢复", confirmation_date=batch.business_date, risk_acknowledged=True, actor="finance")
```

Also test risk acknowledgement false, date mismatch, new import after reset, new manual zero after reset, closed batch and extraction rollback.

- [ ] **Step 2: Run tests and verify RED**

Run: `'/Users/croodslee/Vibe Coding/Financial-Reconciliation-Platform/venv/bin/python' -m pytest backend/tests/test_import_versioning.py backend/tests/test_api_contracts.py -q`
Expected: FAIL because snapshot fields and restore endpoint do not exist.

- [ ] **Step 3: Extend reset audit and implement restore**

```python
def _latest_unrestored_reset_event(db: Session, batch_id: int) -> AuditEvent:
    resets = db.query(AuditEvent).filter_by(batch_id=batch_id, event_type="batch_current_data_reset").order_by(AuditEvent.id.desc()).all()
    restored_ids = {row.event_data["reset_event_id"] for row in db.query(AuditEvent).filter_by(batch_id=batch_id, event_type="batch_reset_restored").all()}
    event = next((row for row in resets if row.id not in restored_ids), None)
    if event is None:
        raise ImportVersionConflictError("没有可恢复的整批重置")
    return event

def restore_last_reset(db: Session, *, batch_id: int, reason: str, confirmation_date: date, risk_acknowledged: bool, actor: str) -> ReconciliationBatch:
    batch = _locked_open_batch(db, batch_id)
    reset_event = _latest_unrestored_reset_event(db, batch.id)
    _validate_reset_restore_state(db, batch, confirmation_date, risk_acknowledged)
    for file_id in reset_event.event_data["current_file_ids"]:
        _restore_snapshot_file(db, batch, file_id, actor)
    for scope in reset_event.event_data["manual_zero_scopes"]:
        _restore_manual_zero(db, batch, scope, actor)
    reconcile_batch(db, batch.id)
    batch.version += 1
    _record_reset_restored(db, batch, reset_event.id, reason, actor)
    return batch
```

The batch detail route calls `_latest_unrestored_reset_event` in a non-throwing eligibility helper and returns the two new fields for the UI.

Eligibility requires zero current files and no coverage in `present_data`, `present_zero` or `attention_required`. Restore each snapshot file using a new ExtractionRun, restore manual-zero scopes only after file extraction, reconcile, increment version, and add `batch_reset_restored` referencing `reset_event_id`.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `'/Users/croodslee/Vibe Coding/Financial-Reconciliation-Platform/venv/bin/python' -m pytest backend/tests/test_import_versioning.py backend/tests/test_api_contracts.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/import_command.py backend/app/schemas/batch.py backend/app/services/import_version_service.py backend/app/api/batches.py backend/tests/test_import_versioning.py backend/tests/test_api_contracts.py
git commit -m "feat: 支持恢复上一次整批重置"
```

### Task 6: 文件恢复及批次恢复界面

**Files:**
- Modify: `frontend/src/services/api.ts`
- Modify: `frontend/src/views/ImportCenter.vue`

**Interfaces:**
- Consumes: file restore and batch restore APIs from Tasks 4–5。
- Produces: `api.restoreImportFile` and `api.restoreLastReset`。

- [ ] **Step 1: Add API methods**

```ts
restoreImportFile: (fileId: number, reason: string) => client.post(`/files/${fileId}/restore`, { reason }),
restoreLastReset: (batchId: number, reason: string, confirmationDate: string) =>
  client.post(`/batches/${batchId}/restore-last-reset`, { reason, confirmation_date: confirmationDate, risk_acknowledged: true })
```

- [ ] **Step 2: Add historical-file restore modal**

Historical rows display “恢复为当前版本”. The modal shows filename, original template, affected scope, reason input and “将重新提取并自动对账”.

- [ ] **Step 3: Strengthen reset modal**

Add `resetRiskAcknowledged`; reset submit remains disabled until reason, exact date and checkbox are all valid. Send `risk_acknowledged: true`.

- [ ] **Step 4: Add restore-last-reset modal**

Show the action only when the backend batch detail exposes `can_restore_last_reset: true`; require reason, exact date and risk checkbox. On success refresh files, coverages, issues and results.

- [ ] **Step 5: Build and commit**

Run: `cd frontend && npm run build`
Expected: PASS.

```bash
git add frontend/src/services/api.ts frontend/src/views/ImportCenter.vue
git commit -m "feat: 增加文件和整批重置恢复界面"
```

### Task 7: 主数据停用语义与别名改绑审计

**Files:**
- Modify: `backend/app/schemas/store.py`
- Modify: `backend/app/services/store_resolution.py`
- Modify: `backend/app/api/stores.py`
- Modify: `backend/app/api/mappings.py`
- Create: `backend/app/services/master_data_service.py`
- Modify: `backend/app/crud/reconciliation.py`
- Test: `backend/tests/test_master_data_safety.py`
- Test: `backend/tests/test_store_resolution.py`
- Modify: `frontend/src/services/api.ts`
- Modify: `frontend/src/views/StoreSettings.vue`
- Modify: `frontend/src/views/MappingSettings.vue`
- Modify: `frontend/src/views/ReconciliationList.vue`

**Interfaces:**
- Changes: alias confirm/update accepts optional reason; rebind to a different store requires a reason.
- Produces: `set_store_active(db, *, store_id, is_active, actor, reason) -> Store` and `set_field_mapping_active(db, *, mapping_id, is_active, actor, reason) -> FieldMapping` in `master_data_service.py`.
- Produces: audit events for alias old/new binding, reconciliation result updates, store enable/disable and field mapping enable/disable.

- [ ] **Step 1: Write failing backend tests**

```python
def test_alias_rebind_requires_reason_and_audits_old_new_store(db_session):
    with pytest.raises(ValueError, match="重新绑定必须填写原因"):
        confirm_alias(db_session, alias_id=alias.id, store_id=new_store.id, actor="admin")
    confirm_alias(db_session, alias_id=alias.id, store_id=new_store.id, actor="admin", reason="原门店选择错误")
    assert audit.event_data["previous_store_id"] == old_store.id
    assert audit.event_data["new_store_id"] == new_store.id

def test_store_with_current_open_batch_data_cannot_be_disabled(db_session):
    with pytest.raises(ValueError, match="当前未关账批次仍有数据"):
        set_store_active(db_session, store_id=store.id, is_active=False, actor="admin", reason="测试停用")

def test_reconciliation_resolution_update_is_audited(db_session):
    update_reconciliation_result(db_session, result.id, ReconciliationResultUpdate(is_resolved=True, remarks="已核实"), actor="finance")
    assert audit.event_type == "reconciliation_result_updated"
    assert audit.event_data["new_is_resolved"] is True
```

- [ ] **Step 2: Run tests and verify RED**

Run: `'/Users/croodslee/Vibe Coding/Financial-Reconciliation-Platform/venv/bin/python' -m pytest backend/tests/test_master_data_safety.py backend/tests/test_store_resolution.py backend/tests/test_api_contracts.py -q`
Expected: FAIL on missing validation/audits.

- [ ] **Step 3: Implement backend validation and audit**

`confirm_alias(db, *, alias_id: int, store_id: int, actor: str, reason: str | None = None)` records `previous_store_id`, `new_store_id`, reason and current run IDs. Store deactivation rejects current CleanData in non-closed batches. Update APIs keep existing URLs for compatibility but record explicit enable/disable events.

- [ ] **Step 4: Update UI semantics**

Remove “删除” wording and destructive delete buttons. Use “停用/重新启用”; deactivation opens an impact modal. Alias rebind modal displays old → new and requires reason. Closing opens a confirmation modal. Difference resolution continues to be editable.

- [ ] **Step 5: Verify and commit**

Run: `'/Users/croodslee/Vibe Coding/Financial-Reconciliation-Platform/venv/bin/python' -m pytest backend/tests/test_master_data_safety.py backend/tests/test_store_resolution.py backend/tests/test_api_contracts.py -q`
Run: `cd frontend && npm run build`
Expected: both PASS.

```bash
git add backend/app/schemas/store.py backend/app/services/store_resolution.py backend/app/services/master_data_service.py backend/app/api/stores.py backend/app/api/mappings.py backend/app/crud/reconciliation.py backend/tests/test_master_data_safety.py backend/tests/test_store_resolution.py frontend/src/services/api.ts frontend/src/views/StoreSettings.vue frontend/src/views/MappingSettings.vue frontend/src/views/ReconciliationList.vue
git commit -m "feat: 完善主数据误操作防护与审计"
```

### Task 8: Full regression, code review and acceptance

**Files:**
- Modify only files directly required by review findings.

**Interfaces:**
- Consumes all previous tasks.
- Produces a clean, reviewed feature branch.

- [ ] **Step 1: Run complete backend suite**

Run: `'/Users/croodslee/Vibe Coding/Financial-Reconciliation-Platform/venv/bin/python' -m pytest -q`
Expected: 0 failures.

- [ ] **Step 2: Run real example acceptance**

Run: `'/Users/croodslee/Vibe Coding/Financial-Reconciliation-Platform/venv/bin/python' -m pytest backend/tests/test_example_acceptance.py -q`
Expected: PASS for 民院店 2026-07-10.

- [ ] **Step 3: Run frontend production build**

Run: `cd frontend && npm run build`
Expected: TypeScript and Vite build PASS.

- [ ] **Step 4: Review invariants**

Check with `git diff --check` and code inspection:

- no physical deletion;
- no historical extraction path;
- restore transaction rollback;
- no duplicate current files or amounts;
- closed-batch gates;
- server-session actor only;
- reasons and confirmations enforced server-side;
- audit snapshots remain small;
- all raw/history rows preserved.

- [ ] **Step 5: Fix findings with a failing test first**

For every blocking finding, add a focused failing test, run it RED, apply the minimal fix, then repeat Steps 1–4.

- [ ] **Step 6: Commit final fixes if any**

```bash
git add backend frontend/src
git commit -m "fix: 完善误操作恢复边界"
```

Skip this commit when review produces no code changes.

## Completion Criteria

- 确认零必须经过明确二次确认，人工零可以撤销为缺失。
- 被作废或替换的文件可以安全恢复且不双计。
- 整批重置可以在无后续数据修改时恢复一次。
- 历史文件和历史运行不能通过别名改绑重新进入当前计算。
- 所有“删除”语义改为可恢复的停用/启用。
- 高风险操作具备原因、日期、风险声明和审计。
- 后端全量测试、民院真实样例和前端生产构建全部通过。
