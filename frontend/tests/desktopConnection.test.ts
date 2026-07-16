import assert from 'node:assert/strict';
import test from 'node:test';

import { createDesktopConnection } from '../src/services/desktopConnection.ts';

const runtime = { location: { protocol: 'https:', hostname: 'tauri.localhost' } };

test('并发请求共享同一次桌面配置加载', async () => {
  let calls = 0;
  const connection = createDesktopConnection(async () => {
    calls += 1;
    return { api_base_url: 'http://127.0.0.1:43123/api/v1', token: 'per-launch-secret' };
  });
  const [first, second] = await Promise.all([
    connection.get(runtime),
    connection.get(runtime),
  ]);
  assert.equal(calls, 1);
  assert.deepEqual(first, second);
});

test('失败不会被缓存且下一次可以重试', async () => {
  let calls = 0;
  const connection = createDesktopConnection(async () => {
    calls += 1;
    if (calls === 1) throw new Error('cold start failed');
    return { api_base_url: 'http://127.0.0.1:43123/api/v1', token: 'per-launch-secret' };
  });
  await assert.rejects(connection.get(runtime), /cold start failed/);
  assert.equal((await connection.get(runtime))?.token, 'per-launch-secret');
  assert.equal(calls, 2);
});
