import assert from 'node:assert/strict';
import test from 'node:test';

import { createLatestCalendarRangeLoader } from '../src/services/calendarTrends.ts';

type Range = { startDate: string; endDate: string };

const deferred = <T>() => {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
};

test('月份快速切换时丢弃后返回的旧月份响应', async () => {
  const january = deferred<string[]>();
  const february = deferred<string[]>();
  let currentRange: Range = { startDate: '2026-01-26', endDate: '2026-03-08' };
  const loader = createLatestCalendarRangeLoader<string[]>((range) => (
    range.startDate === '2025-12-29' ? january.promise : february.promise
  ));

  const first = loader(
    { startDate: '2025-12-29', endDate: '2026-02-08' },
    () => currentRange,
  );
  const second = loader(currentRange, () => currentRange);

  february.resolve(['二月']);
  assert.deepEqual(await second, ['二月']);
  january.resolve(['一月']);
  assert.equal(await first, null);
});

test('当前日历范围已经变化时丢弃响应', async () => {
  const response = deferred<string[]>();
  let currentRange: Range = { startDate: '2025-12-29', endDate: '2026-02-08' };
  const loader = createLatestCalendarRangeLoader<string[]>(() => response.promise);
  const loading = loader(currentRange, () => currentRange);

  currentRange = { startDate: '2026-01-26', endDate: '2026-03-08' };
  response.resolve(['一月']);

  assert.equal(await loading, null);
});
