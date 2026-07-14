import assert from 'node:assert/strict';
import test from 'node:test';

import { loadExistingBatchForDate } from '../src/services/importBatchLoader.ts';

type TestBatch = { id: number; business_date: string };
type TestDetail = { batchId: number };

const deferred = <T>() => {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
};

test('批次列表返回前切换账期时丢弃旧请求且不加载详情', async () => {
  const batches = deferred<TestBatch[]>();
  let currentBusinessDate = '2026-07-10';
  let detailCalls = 0;
  const loading = loadExistingBatchForDate<TestBatch, TestDetail>({
    requestedBusinessDate: '2026-07-10',
    getCurrentBusinessDate: () => currentBusinessDate,
    getBatches: () => batches.promise,
    getBatchDetail: async (batchId) => {
      detailCalls += 1;
      return { batchId };
    },
  });

  currentBusinessDate = '2026-07-11';
  batches.resolve([{ id: 1, business_date: '2026-07-10' }]);

  assert.equal(await loading, null);
  assert.equal(detailCalls, 0);
});

test('批次详情返回前切换账期时丢弃旧请求结果', async () => {
  const detail = deferred<TestDetail>();
  const detailStarted = deferred<void>();
  let currentBusinessDate = '2026-07-10';
  const loading = loadExistingBatchForDate<TestBatch, TestDetail>({
    requestedBusinessDate: '2026-07-10',
    getCurrentBusinessDate: () => currentBusinessDate,
    getBatches: async () => [{ id: 1, business_date: '2026-07-10' }],
    getBatchDetail: (batchId) => {
      assert.equal(batchId, 1);
      detailStarted.resolve(undefined);
      return detail.promise;
    },
  });

  await detailStarted.promise;
  currentBusinessDate = '2026-07-11';
  detail.resolve({ batchId: 1 });

  assert.equal(await loading, null);
});
