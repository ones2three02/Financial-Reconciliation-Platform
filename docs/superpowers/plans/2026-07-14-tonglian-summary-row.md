# 通联汇总行识别 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让完整通联导出文件安全跳过明确的表尾汇总行，同时继续阻断普通业务行中的错误日期。

**Architecture:** 在提取模板中声明允许的汇总日期标记，并由独立的行分类函数执行严格判断。预检、RawData 持久化和正式提取共同调用该函数，避免三个阶段规则漂移。

**Tech Stack:** Python 3.14、FastAPI、openpyxl、SQLAlchemy 2、pytest

## Global Constraints

- 仅 `tonglian_v1` 允许日期标记“汇总”。
- 只有“日期等于汇总且门店为空”时才跳过该行。
- 普通日期错误必须阻断导入，错误信息包含模板、工作表和 Excel 行号，但不回显原值。
- 不修改原始工作簿，不放宽其他模板校验，不改变对账公式。

---

### Task 1: 共享行分类与预检

**Files:**
- Create: `backend/app/services/workbook_rows.py`
- Modify: `backend/app/domain/extraction_profiles.py:8-93`
- Modify: `backend/app/services/workbook_preflight.py:99-126`
- Test: `backend/tests/test_workbook_preflight.py`

**Interfaces:**
- Consumes: `ProfileDefinition.date_column`、`ProfileDefinition.store_column`。
- Produces: `is_summary_row(profile: ProfileDefinition, content: Mapping[str, object]) -> bool`。

- [ ] **Step 1: 写入失败测试**

在 `backend/tests/test_workbook_preflight.py` 增加通联工作簿构造器和两个测试：

```python
def tonglian_workbook_bytes(rows: list[list[object]]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "sheet1"
    sheet.append(["交易统计汇总"])
    sheet.append(["统计日期", "门店名", "成功交易金额"])
    for row in rows:
        sheet.append(row)
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def test_tonglian_profile_ignores_explicit_summary_footer():
    result = preflight_workbook(
        tonglian_workbook_bytes([
            ["2026-07-10", "民院店原始名称", 100],
            ["汇总", None, 100],
        ]),
        profile_code="tonglian_v1",
        business_date=date(2026, 7, 10),
        store_id=None,
    )
    assert result.total_data_rows == 1
    assert result.matching_row_count == 1


def test_tonglian_profile_reports_sheet_and_row_for_bad_business_date():
    with pytest.raises(
        PreflightValidationError,
        match=r"模板 tonglian_v1 工作表 sheet1 第 4 行的统计日期无法解析",
    ):
        preflight_workbook(
            tonglian_workbook_bytes([
                ["2026-07-10", "正常门店", 100],
                ["汇总", "不应被跳过的门店", 50],
            ]),
            profile_code="tonglian_v1",
            business_date=date(2026, 7, 10),
            store_id=None,
        )
```

- [ ] **Step 2: 运行测试并确认红灯**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/croodslee/Vibe\ Coding/Financial-Reconciliation-Platform/venv/bin/python \
  -m pytest -p no:cacheprovider backend/tests/test_workbook_preflight.py \
  -k 'tonglian_profile' -q
```

Expected: 汇总行测试因日期“汇总”无法解析而失败；错误定位测试因当前消息缺少工作表和行号而失败。

- [ ] **Step 3: 实现最小共享分类规则**

在 `ProfileDefinition` 增加：

```python
summary_date_markers: tuple[str, ...] = ()
```

仅在 `tonglian_v1` 配置中增加：

```python
summary_date_markers=("汇总",),
```

创建 `backend/app/services/workbook_rows.py`：

```python
from collections.abc import Mapping

from backend.app.domain.extraction_profiles import ProfileDefinition


def is_summary_row(
    profile: ProfileDefinition,
    content: Mapping[str, object],
) -> bool:
    if not profile.summary_date_markers or profile.store_column is None:
        return False
    raw_date = str(content.get(profile.date_column) or "").strip()
    raw_store = str(content.get(profile.store_column) or "").strip()
    return raw_date in profile.summary_date_markers and not raw_store
```

预检循环改为携带 Excel 行号、构造按列名索引的 `content_row`，先跳过汇总行再统计；解析失败改为：

```python
for excel_row_number, row in enumerate(
    sheet.iter_rows(min_row=profile.header_row + 1, values_only=True),
    start=profile.header_row + 1,
):
    if not any(value not in (None, "") for value in row):
        continue
    content_row = {
        header: row[index] if index < len(row) else None
        for index, header in enumerate(headers)
    }
    if is_summary_row(profile, content_row):
        continue
    total_data_rows += 1
    try:
        row_date = _parse_date(row[date_index])
    except (ValueError, TypeError, IndexError) as exc:
        raise PreflightValidationError(
            f"模板 {profile.code} 工作表 {sheet_name} 第 {excel_row_number} 行的"
            f"{profile.date_column}无法解析"
        ) from exc
```

- [ ] **Step 4: 运行预检测试并确认绿灯**

Run: 与 Step 2 相同。

Expected: `2 passed`。

- [ ] **Step 5: 提交**

```bash
git add backend/app/domain/extraction_profiles.py \
  backend/app/services/workbook_rows.py \
  backend/app/services/workbook_preflight.py \
  backend/tests/test_workbook_preflight.py
git commit -m "fix: 识别通联表尾汇总行"
```

### Task 2: RawData 与提取阶段防御

**Files:**
- Modify: `backend/app/services/import_pipeline.py:66-103`
- Modify: `backend/app/services/extraction_engine.py:232-250`
- Test: `backend/tests/test_example_acceptance.py`

**Interfaces:**
- Consumes: Task 1 的 `is_summary_row`。
- Produces: 完整通联示例文件可导入，且 RawData 和 CleanData 均不包含汇总行。

- [ ] **Step 1: 写入完整示例失败测试**

```python
from backend.app.models.raw_data import RawData


def test_full_tonglian_example_excludes_summary_footer(db_session):
    batch = get_or_create_batch(db_session, BUSINESS_DATE, actor="admin")
    outcome = import_workbook(
        db_session,
        ImportWorkbookCommand(
            batch_id=batch.id,
            filename="通联好老板.xlsx",
            content=(EXAMPLE_DIR / "通联好老板.xlsx").read_bytes(),
            profile_code="tonglian_v1",
            store_id=None,
            actor="admin",
        ),
    )
    raw_rows = (
        db_session.query(RawData)
        .filter(RawData.import_file_id == outcome.import_file_id)
        .all()
    )
    assert len(raw_rows) == 16
    assert all(row.content.get("统计日期") != "汇总" for row in raw_rows)
    assert outcome.status == "attention_required"
```

- [ ] **Step 2: 运行测试并确认红灯**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/croodslee/Vibe\ Coding/Financial-Reconciliation-Platform/venv/bin/python \
  -m pytest -p no:cacheprovider \
  backend/tests/test_example_acceptance.py::test_full_tonglian_example_excludes_summary_footer -q
```

Expected: 提取阶段仍尝试解析日期“汇总”并失败。

- [ ] **Step 3: 在持久化和提取中使用共享分类**

`_persist_raw_rows` 在创建 RawData 前增加：

```python
content_row = {
    header: _json_safe(values[index] if index < len(values) else None)
    for index, header in enumerate(headers)
}
if is_summary_row(profile, content_row):
    continue
```

`_extract_channel_rows` 在解析日期前增加：

```python
content = raw_row.content or {}
if is_summary_row(profile, content):
    continue
if clean_date(content.get(profile.date_column)) != batch.business_date:
    continue
```

- [ ] **Step 4: 运行完整示例测试并确认绿灯**

Run: 与 Step 2 相同。

Expected: `1 passed`，RawData 恰好 16 行。

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/import_pipeline.py \
  backend/app/services/extraction_engine.py \
  backend/tests/test_example_acceptance.py
git commit -m "fix: 从导入数据中排除通联汇总行"
```

### Task 3: 后端完整回归

**Files:**
- Verify only

**Interfaces:**
- Consumes: Task 1、Task 2 的全部实现。
- Produces: 后端测试套件和代码差异检查通过。

- [ ] **Step 1: 运行完整后端测试**

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/croodslee/Vibe\ Coding/Financial-Reconciliation-Platform/venv/bin/python \
  -m pytest -p no:cacheprovider backend/tests -q
```

Expected: 所有测试通过，失败数为 0。

- [ ] **Step 2: 检查差异格式**

```bash
git diff --check
```

Expected: 无输出，退出码为 0。
