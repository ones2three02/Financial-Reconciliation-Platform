# Web 主线代码审查问题修复实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 `main` 分支代码审查确认的财务完整性、别名确认、分页、权限、Dashboard 日期范围和月历异步竞态问题，并完成可推送的验证闭环。

**Architecture:** 后端在服务层按未解决问题的数据来源保守判定结果完整性，并在趋势聚合入口统一验证日期范围。前端增加两个无依赖的小型服务模块：一个负责别名分页与问题解析，一个负责丢弃陈旧月历响应；页面只负责调用和展示。

**Tech Stack:** FastAPI、SQLAlchemy、Pytest、Vue 3、TypeScript、Node.js 22、Node test runner、Vite。

## Global Constraints

- 不修改数据库结构，不新增迁移。
- 不升级或新增依赖。
- 代码标识符使用英文；测试名称、注释和提交信息使用中文。
- 直接在已隔离的 `main` worktree 实施，完成全部门禁后推送 `origin/main`。
- 每项修复遵循 RED → GREEN → REFACTOR，不先写实现。

---

### Task 1: 保守处理未解决质量问题

**Files:**
- Modify: `backend/tests/test_reconciliation_batch.py`
- Modify: `backend/app/services/reconciliation_service.py:214-308`

**Interfaces:**
- Consumes: `DataQualityIssue.source_code`、`StoreSourceRequirement.requirement`、`reconcile_batch(db, batch_id)`。
- Produces: 只有需要受影响来源的门店被标记为 `incomplete`；`not_required` 门店保持按自身覆盖情况计算。

- [ ] **Step 1: 写失败测试**

增加测试：完整覆盖的门店遇到 open `meituan` 质量问题时必须为 `incomplete`；同一来源配置为 `not_required` 时不受影响。测试使用现有 `setup_batch`、`add_balanced_coverage`，并新增 `StoreSourceRequirement` 测试数据。

```python
result = reconcile_batch(db_session, batch.id)[0]
assert result.status == "incomplete"
assert result.completeness_status == "incomplete"
```

- [ ] **Step 2: 验证 RED**

```bash
/Users/croodslee/Vibe\ Coding/Financial-Reconciliation-Platform/venv/bin/python -m pytest -p no:cacheprovider backend/tests/test_reconciliation_batch.py -q
```

预期：需要该来源的新增测试失败，当前结果错误地是 `consistent/complete`。

- [ ] **Step 3: 写最小实现**

查询当前批次 open issue 的 `source_code` 集合。读取门店覆盖后，若该来源不是 `not_required` 且存在 open issue，则加入 `incomplete_sources`；保留当前已确认金额用于暂定差额计算。

```python
open_issue_sources = {
    source_code
    for (source_code,) in db.query(DataQualityIssue.source_code).filter(
        DataQualityIssue.batch_id == batch.id,
        DataQualityIssue.status == "open",
    )
}
```

- [ ] **Step 4: 验证 GREEN 并提交**

目标测试全部通过后提交：

```bash
git add backend/app/services/reconciliation_service.py backend/tests/test_reconciliation_batch.py
git commit -m "fix: 保守处理未确认门店金额"
```

---

### Task 2: 限制 Dashboard 趋势日期范围

**Files:**
- Modify: `backend/tests/test_dashboard_aggregates.py`
- Modify: `backend/tests/test_api_contracts.py`
- Modify: `backend/app/crud/reconciliation.py:106-156`
- Modify: `backend/app/api/dashboard.py:20-32`

**Interfaces:**
- Consumes: `get_dashboard_trends(db, days, start_date, end_date)`。
- Produces: 最大 180 天的有界趋势列表；非法范围在 API 层转换为 HTTP 422。

- [ ] **Step 1: 写失败测试**

覆盖日期只传一端、倒序、超过 180 天时抛出 `ValueError`；`date.max` 单日范围返回一条记录。API 契约测试直接调用 `read_dashboard_trends`，断言 `ValueError` 被转换为 422。

```python
with pytest.raises(ValueError):
    get_dashboard_trends(
        db_session,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 6, 30),
    )

rows = get_dashboard_trends(db_session, start_date=date.max, end_date=date.max)
assert [row["date"] for row in rows] == [date.max.isoformat()]
```

- [ ] **Step 2: 验证 RED**

运行 `test_dashboard_aggregates.py` 和 `test_api_contracts.py`，预期非法范围与 `date.max` 测试失败。

- [ ] **Step 3: 写最小实现**

在 CRUD 中增加 `MAX_TREND_RANGE_DAYS = 180` 和 `_resolve_dashboard_trend_range`，统一返回 `(start_date, end_date, range_days)`；使用 `for offset in range(range_days)` 填充日期。API 层捕获 `ValueError` 并抛出 `HTTPException(status_code=422, detail=str(exc))`。

- [ ] **Step 4: 验证 GREEN 并提交**

```bash
git add backend/app/api/dashboard.py backend/app/crud/reconciliation.py backend/tests/test_dashboard_aggregates.py backend/tests/test_api_contracts.py
git commit -m "fix: 限制看板趋势查询范围"
```

---

### Task 3: 统一别名分页、解析与权限

**Files:**
- Create: `frontend/src/services/storeAliases.ts`
- Create: `frontend/tests/storeAliases.test.ts`
- Modify: `frontend/src/services/api.ts:294-311`
- Modify: `frontend/src/views/ImportCenter.vue:313-570`
- Modify: `frontend/src/views/ReconciliationList.vue:491-665`
- Modify: `frontend/src/views/StoreSettings.vue:500-626`

**Interfaces:**
- Produces: `loadAllPages<T>(loadPage, pageSize)`、`findAliasForIssue(aliases, issue)`、`canConfirmAlias(role)`。
- Produces: `api.getStoreAliases(status, skip, limit)` 与 `api.getAllStoreAliases(status)`。
- Consumers: 三个 Vue 页面。

- [ ] **Step 1: 写失败测试**

创建 `storeAliases.test.ts`，验证两页数据合并、使用 `source_code + raw_value` 得到真实 alias ID、只有 `admin` 可确认。

```typescript
const alias = findAliasForIssue(
  [{ id: 41, source_code: 'meituan', alias_name: '原始店名' }],
  { id: 7, source_code: 'meituan', raw_value: '原始店名' },
);
assert.equal(alias?.id, 41);
assert.equal(canConfirmAlias('finance'), false);
```

- [ ] **Step 2: 验证 RED**

```bash
PATH=/Users/croodslee/.local/share/mise/installs/node/22/bin:$PATH npm --prefix frontend test
```

预期：新模块不存在，新增测试失败。

- [ ] **Step 3: 写最小实现**

实现纯函数模块；API 按 200 条一页加载直到最后一页。StoreSettings 加载完整集合；ReconciliationList 加载全部 pending；ImportCenter 打开确认弹窗时加载 pending，并提交 `findAliasForIssue` 得到的 `alias.id`。ImportCenter 使用 `canConfirmAlias` 控制入口和按钮。

- [ ] **Step 4: 验证 GREEN 并提交**

```bash
git add frontend/src/services/api.ts frontend/src/services/storeAliases.ts frontend/src/views/ImportCenter.vue frontend/src/views/ReconciliationList.vue frontend/src/views/StoreSettings.vue frontend/tests/storeAliases.test.ts
git commit -m "fix: 统一门店别名确认与分页"
```

---

### Task 4: 防止旧月份响应覆盖月历

**Files:**
- Create: `frontend/src/services/calendarTrends.ts`
- Create: `frontend/tests/calendarTrends.test.ts`
- Modify: `frontend/src/views/Dashboard.vue:387-529`

**Interfaces:**
- Produces: `createLatestRangeLoader<T>(loadRange)`，返回仅接受最新且仍匹配当前范围的异步加载函数。
- Consumes: `api.getDashboardTrends({start_date, end_date})`。

- [ ] **Step 1: 写失败测试**

用两个 deferred Promise 模拟“新请求先返回、旧请求后返回”，断言新请求返回数据、旧请求返回 `null`。

```typescript
const oldRequest = loadLatest(julyRange, () => currentRange);
const newRequest = loadLatest(augustRange, () => currentRange);
august.resolve(['august']);
assert.deepEqual(await newRequest, ['august']);
july.resolve(['july']);
assert.equal(await oldRequest, null);
```

- [ ] **Step 2: 验证 RED**

运行前端全部测试，预期新模块不存在导致测试失败。

- [ ] **Step 3: 写最小实现**

实现递增 request id 和范围相等判断。Dashboard 增加 `currentCalendarRange()`，只有 loader 返回非 `null` 时才写入 `calendarDataMap`。

- [ ] **Step 4: 验证 GREEN 并提交**

运行前端全部测试和生产构建后提交：

```bash
git add frontend/src/services/calendarTrends.ts frontend/src/views/Dashboard.vue frontend/tests/calendarTrends.test.ts
git commit -m "fix: 丢弃月历陈旧响应"
```

---

### Task 5: 清理与完整交付门禁

**Files:**
- Modify: 本任务审查范围内仍有行尾空格的文件，仅删除行尾空格。

**Interfaces:**
- Produces: 干净差异、完整验证记录和已推送的 `origin/main`。

- [ ] **Step 1: 清理行尾空格**

仅对 `bd72cb1..HEAD` 涉及且仍在本任务范围内的文本文件做机械清理，不调整其他格式。

- [ ] **Step 2: 运行完整验证**

```bash
/Users/croodslee/Vibe\ Coding/Financial-Reconciliation-Platform/venv/bin/python -m pytest -p no:cacheprovider backend/tests -q
PATH=/Users/croodslee/.local/share/mise/installs/node/22/bin:$PATH npm --prefix frontend test
PATH=/Users/croodslee/.local/share/mise/installs/node/22/bin:$PATH npm --prefix frontend run build
git diff --check origin/main..HEAD
git status --short --branch
```

预期：全部命令退出码为 0，`git diff --check` 无输出，工作树干净。

- [ ] **Step 3: 审查、提交机械清理并推送**

检查 `git diff origin/main..HEAD --stat`、提交列表和关键差异，确认没有数据库迁移、依赖变更或无关文件。如有机械清理，提交 `style: 清理 Web 主线行尾空格`。随后执行：

```bash
git push origin main
git rev-list --left-right --count main...origin/main
```

预期：返回 `0 0`。
