import assert from 'node:assert/strict';
import test from 'node:test';

import {
  clearQueue,
  createQueueItems,
  getQueue,
  isCurrentImportContext,
  prepareQueueItemRetry,
  queueKey,
  replaceQueue,
  runWithProcessing,
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
    item('待确认.xlsx', 'attention', context),
  ];
  const queues = replaceQueue({}, context, files);
  assert.deepEqual(runnableItems(files).map((entry) => entry.file.name), ['待处理.xlsx', '失败.xlsx']);
  assert.deepEqual(summarizeProfileQueue(queues, '2026-07-10', 'meituan_v1'), {
    pending: 1,
    failed: 1,
    completed: 3,
  });
});

test('创建队列项时复制上下文且不受后续选择变化影响', () => {
  const original: ImportQueueContext = { businessDate: '2026-07-10', profileCode: 'store_finance_v1', storeId: 1 };
  const [entry] = createQueueItems([{ name: '美团.xlsx' }], original, (file) => file.name);
  original.businessDate = '2026-07-11';
  original.profileCode = 'douyin_v1';
  original.storeId = 2;
  assert.deepEqual(entry?.context, {
    businessDate: '2026-07-10',
    profileCode: 'store_finance_v1',
    storeId: 1,
  });
});

test('处理流程抛错时仍恢复非处理中状态', async () => {
  const processingStates: boolean[] = [];
  await assert.rejects(
    runWithProcessing(
      (processing) => processingStates.push(processing),
      async () => { throw new Error('刷新失败'); },
    ),
    /刷新失败/,
  );
  assert.deepEqual(processingStates, [true, false]);
});

test('导入上下文账期与当前账期不一致时拒绝更新页面状态', () => {
  const context = { businessDate: '2026-07-10', profileCode: 'meituan_v1', storeId: null };
  assert.equal(isCurrentImportContext(context, '2026-07-11'), false);
  assert.equal(isCurrentImportContext(context, '2026-07-10'), true);
});

test('失败项重试前清除旧错误和旧预检结果', () => {
  const context = { businessDate: '2026-07-10', profileCode: 'meituan_v1', storeId: null };
  const failedItem: ImportQueueItem<TestFile> = {
    ...item('失败.xlsx', 'failed', context),
    error: '上次导入失败',
    preflight: { sheetName: '旧结果' },
  };
  const prepared = prepareQueueItemRetry(failedItem);
  assert.equal(prepared.status, 'ready');
  assert.equal(prepared.error, undefined);
  assert.equal(prepared.preflight, undefined);
});
