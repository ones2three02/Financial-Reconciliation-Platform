# 文件导入独立队列 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为每个账期、模板和文件级门店维护独立的临时文件队列，杜绝文件被错误模板或门店重复处理。

**Architecture:** 将队列键、不可变上下文、队列读写和状态统计提取为纯 TypeScript 模块；Vue 页面只管理当前选择和调用 API。导入开始时固定批次与队列项上下文，完成状态不再进入后续重试。

**Tech Stack:** Vue 3.5、TypeScript 6、Node 22 内置测试运行器、Vite 8

## Global Constraints

- 不新增 npm 依赖。
- 渠道队列按“账期 + 模板”隔离，门店财务表按“账期 + 模板 + 门店”隔离。
- 切换账期清空全部临时队列；切换模板或门店只切换可见队列。
- 只有 `ready`、`failed` 状态允许提交；已完成状态只展示，不重复导入。
- 每个请求使用选择文件时绑定的上下文，不读取循环过程中的可变界面选择。

---

### Task 1: 纯队列状态模块

**Files:**
- Create: `frontend/src/services/importQueue.ts`
- Create: `frontend/tests/importQueue.test.ts`
- Modify: `frontend/package.json`

**Interfaces:**
- Produces: `ImportQueueContext`、`ImportQueueItem<TFile>`、`ImportQueueMap<TFile>`、`queueKey`、`getQueue`、`replaceQueue`、`clearQueue`、`runnableItems`、`summarizeProfileQueue`。

- [ ] **Step 1: 写入失败测试**

创建 `frontend/tests/importQueue.test.ts`：

```typescript
import assert from 'node:assert/strict';
import test from 'node:test';

import {
  clearQueue,
  getQueue,
  queueKey,
  replaceQueue,
  runnableItems,
  summarizeProfileQueue,
  type ImportQueueContext,
  type ImportQueueItem,
  type ImportQueueMap,
} from '../src/services/importQueue.ts';

type TestFile = { name: string };

const item = (
  name: string,
  status: ImportQueueItem<TestFile>['status'],
  context: ImportQueueContext,
): ImportQueueItem<TestFile> => ({
  key: name,
  file: { name },
  status,
  context,
});

test('模板和财务门店使用互不相同的队列键', () => {
  assert.notEqual(
    queueKey({ businessDate: '2026-07-10', profileCode: 'meituan_v1', storeId: null }),
    queueKey({ businessDate: '2026-07-10', profileCode: 'douyin_v1', storeId: null }),
  );
  assert.notEqual(
    queueKey({ businessDate: '2026-07-10', profileCode: 'store_finance_v1', storeId: 1 }),
    queueKey({ businessDate: '2026-07-10', profileCode: 'store_finance_v1', storeId: 2 }),
  );
});

test('切换上下文保留各自队列且只清空目标队列', () => {
  const meituan = { businessDate: '2026-07-10', profileCode: 'meituan_v1', storeId: null };
  const douyin = { businessDate: '2026-07-10', profileCode: 'douyin_v1', storeId: null };
  let queues: ImportQueueMap<TestFile> = {};
  queues = replaceQueue(queues, meituan, [item('美团.xlsx', 'imported', meituan)]);
  queues = replaceQueue(queues, douyin, [item('抖音.xlsx', 'ready', douyin)]);
  assert.equal(getQueue(queues, meituan)[0]?.file.name, '美团.xlsx');
  assert.equal(getQueue(queues, douyin)[0]?.file.name, '抖音.xlsx');
  queues = clearQueue(queues, douyin);
  assert.equal(getQueue(queues, douyin).length, 0);
  assert.equal(getQueue(queues, meituan).length, 1);
});

test('仅待处理和失败文件可执行并正确汇总模板状态', () => {
  const context = { businessDate: '2026-07-10', profileCode: 'meituan_v1', storeId: null };
  const files = [
    item('待处理.xlsx', 'ready', context),
    item('失败.xlsx', 'failed', context),
    item('完成.xlsx', 'imported', context),
    item('重复.xlsx', 'duplicate', context),
  ];
  const queues = replaceQueue({}, context, files);
  assert.deepEqual(runnableItems(files).map((entry) => entry.file.name), ['待处理.xlsx', '失败.xlsx']);
  assert.deepEqual(summarizeProfileQueue(queues, '2026-07-10', 'meituan_v1'), {
    pending: 1,
    failed: 1,
    completed: 2,
  });
});
```

在 `frontend/package.json` 的 scripts 中增加：

```json
"test": "node --test tests/*.test.ts"
```

- [ ] **Step 2: 运行测试并确认红灯**

Run: `npm --prefix frontend test`

Expected: 因 `frontend/src/services/importQueue.ts` 不存在而失败。

- [ ] **Step 3: 实现最小纯状态模块**

创建 `frontend/src/services/importQueue.ts`：

```typescript
export type ImportQueueStatus = 'ready' | 'preflighting' | 'importing' | 'imported' | 'duplicate' | 'attention' | 'failed';

export interface ImportQueueContext {
  businessDate: string;
  profileCode: string;
  storeId: number | null;
}

export interface ImportQueueItem<TFile> {
  key: string;
  file: TFile;
  status: ImportQueueStatus;
  context: ImportQueueContext;
  preflight?: unknown;
  error?: string;
}

export type ImportQueueMap<TFile> = Record<string, ImportQueueItem<TFile>[]>;

const completedStatuses = new Set<ImportQueueStatus>(['imported', 'duplicate', 'attention']);

export const queueKey = (context: ImportQueueContext) =>
  `${context.businessDate}::${context.profileCode}::${context.storeId ?? 'none'}`;

export const getQueue = <TFile>(queues: ImportQueueMap<TFile>, context: ImportQueueContext) =>
  queues[queueKey(context)] ?? [];

export const replaceQueue = <TFile>(queues: ImportQueueMap<TFile>, context: ImportQueueContext, items: ImportQueueItem<TFile>[]) => ({
  ...queues,
  [queueKey(context)]: items,
});

export const clearQueue = <TFile>(queues: ImportQueueMap<TFile>, context: ImportQueueContext) => {
  const next = { ...queues };
  delete next[queueKey(context)];
  return next;
};

export const runnableItems = <TFile>(items: ImportQueueItem<TFile>[]) =>
  items.filter((item) => item.status === 'ready' || item.status === 'failed');

export const summarizeProfileQueue = <TFile>(queues: ImportQueueMap<TFile>, businessDate: string, profileCode: string) => {
  const items = Object.values(queues).flat().filter(
    (item) => item.context.businessDate === businessDate && item.context.profileCode === profileCode,
  );
  return {
    pending: items.filter((item) => item.status === 'ready').length,
    failed: items.filter((item) => item.status === 'failed').length,
    completed: items.filter((item) => completedStatuses.has(item.status)).length,
  };
};
```

- [ ] **Step 4: 运行单元测试并确认绿灯**

Run: `npm --prefix frontend test`

Expected: `3 passed`，失败数为 0。

- [ ] **Step 5: 提交**

```bash
git add frontend/package.json frontend/src/services/importQueue.ts frontend/tests/importQueue.test.ts
git commit -m "test: 建立导入队列上下文状态模型"
```

### Task 2: ImportCenter 接入独立队列

**Files:**
- Modify: `frontend/src/views/ImportCenter.vue:52-103,221-325,448-453`
- Test: `frontend/tests/importQueue.test.ts`

**Interfaces:**
- Consumes: Task 1 的全部队列函数和类型。
- Produces: 当前上下文队列、模板状态徽标、不可变导入请求上下文。

- [ ] **Step 1: 补充上下文快照回归测试**

在 `frontend/tests/importQueue.test.ts` 增加：

```typescript
test('队列项保留创建时的上下文快照', () => {
  const original = { businessDate: '2026-07-10', profileCode: 'meituan_v1', storeId: null };
  const entry = item('美团.xlsx', 'ready', { ...original });
  const currentSelection = { ...original, profileCode: 'douyin_v1' };
  assert.equal(entry.context.profileCode, 'meituan_v1');
  assert.equal(currentSelection.profileCode, 'douyin_v1');
});
```

- [ ] **Step 2: 运行测试并确认行为基线**

Run: `npm --prefix frontend test`

Expected: 新测试通过；随后组件改造必须直接使用此上下文而非 `selectedProfile`。

- [ ] **Step 3: 将页面队列改为按上下文索引**

导入 Task 1 模块并替换本地类型：

```typescript
import {
  clearQueue,
  getQueue,
  replaceQueue,
  runnableItems,
  summarizeProfileQueue,
  type ImportQueueContext,
  type ImportQueueItem,
  type ImportQueueMap,
} from '../services/importQueue';

type QueueItem = ImportQueueItem<File> & { preflight?: PreflightResult };

const queues = ref<ImportQueueMap<File>>({});
const currentContext = computed<ImportQueueContext>(() => ({
  businessDate: globalDate.value,
  profileCode: selectedProfile.value,
  storeId: selectedProfile.value === 'store_finance_v1' ? selectedStoreId.value : null,
}));
const queue = computed(() => getQueue(queues.value, currentContext.value) as QueueItem[]);
const actionableQueue = computed(() => runnableItems(queue.value) as QueueItem[]);
const canSelectFiles = computed(() => selectedProfile.value !== 'store_finance_v1' || selectedStoreId.value !== null);
```

`onFilesSelected` 创建不可变上下文快照并只替换当前队列：

```typescript
const context = { ...currentContext.value };
if (!canSelectFiles.value) {
  message.value = { type: 'error', text: '请先选择门店，再选择门店财务表文件。' };
  return;
}
const items = files.map((file, index) => ({
  key: `${file.name}-${file.size}-${index}`,
  file,
  status: 'ready' as const,
  context,
}));
queues.value = replaceQueue(queues.value, context, items);
```

`canImport` 必须使用 `actionableQueue.value.length`；“清空列表”调用：

```typescript
const clearCurrentQueue = () => {
  queues.value = clearQueue(queues.value, currentContext.value);
  message.value = null;
};
```

- [ ] **Step 4: 固定导入过程上下文并禁止重复处理**

`processQueue` 开始时固定上下文、批次和可执行项：

```typescript
const batch = activeBatch.value;
const context = { ...currentContext.value };
const items = [...actionableQueue.value];
if (!batch || !items.length || batch.business_date !== context.businessDate) return;

for (const item of items) {
  item.error = undefined;
  try {
    item.status = 'preflighting';
    item.preflight = await api.preflightWorkbook(
      item.file,
      item.context.profileCode as ProfileCode,
      item.context.businessDate,
      item.context.storeId,
    );
    item.status = 'importing';
    const outcome = await api.importWorkbook(
      item.file,
      batch.id,
      item.context.profileCode as ProfileCode,
      item.context.storeId,
    );
    item.status = outcome.status === 'duplicate'
      ? 'duplicate'
      : outcome.status === 'attention_required'
        ? 'attention'
        : 'imported';
  } catch (error) {
    item.status = 'failed';
    item.error = errorDetail(error);
  }
}

if (globalDate.value === context.businessDate) {
  const detail = await api.getBatchDetail(batch.id);
  batchDetail.value = detail;
  activeBatch.value = detail.batch;
}
```

模板 radio 和门店 Select 增加 `:disabled="processing"`。文件 input 在 `!canSelectFiles || processing` 时禁用。

- [ ] **Step 5: 增加模板状态徽标并清理账期队列**

增加：

```typescript
const profileQueueSummary = (profileCode: ProfileCode) =>
  summarizeProfileQueue(queues.value, globalDate.value, profileCode);

watch(globalDate, () => {
  queues.value = {};
  message.value = null;
  void loadExistingBatch();
});
```

每个模板卡片显示：

```vue
<span v-if="profileQueueSummary(profile.code).pending" class="text-blue-600">
  待导入 {{ profileQueueSummary(profile.code).pending }}
</span>
<span v-if="profileQueueSummary(profile.code).failed" class="text-rose-600">
  失败 {{ profileQueueSummary(profile.code).failed }}
</span>
<span v-if="profileQueueSummary(profile.code).completed" class="text-emerald-600">
  已完成 {{ profileQueueSummary(profile.code).completed }}
</span>
```

- [ ] **Step 6: 运行前端测试和生产构建**

```bash
npm --prefix frontend test
npm --prefix frontend run build
```

Expected: TypeScript 单元测试全部通过；`vue-tsc -b` 和 Vite 构建退出码为 0。

- [ ] **Step 7: 提交**

```bash
git add frontend/src/views/ImportCenter.vue frontend/tests/importQueue.test.ts
git commit -m "fix: 按导入上下文隔离文件队列"
```

### Task 3: 联合验收

**Files:**
- Verify only

**Interfaces:**
- Consumes: 前端独立队列和后端通联汇总行计划的最终结果。
- Produces: 可合并的完整修复分支。

- [ ] **Step 1: 运行所有自动化检查**

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/croodslee/Vibe\ Coding/Financial-Reconciliation-Platform/venv/bin/python \
  -m pytest -p no:cacheprovider backend/tests -q
npm --prefix frontend test
npm --prefix frontend run build
git diff --check
```

Expected: 后端和前端测试失败数均为 0，生产构建和差异检查退出码为 0。

- [ ] **Step 2: 检查变更范围**

```bash
git status --short --branch
git diff main...HEAD --stat
git log --oneline main..HEAD
```

Expected: 仅包含两份已确认规范、两份计划、通联汇总行修复、独立队列模块及 ImportCenter 接入。
