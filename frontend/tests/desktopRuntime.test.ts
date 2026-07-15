import assert from 'node:assert/strict';
import test from 'node:test';

import { loadDesktopBackendConfig } from '../src/services/desktopRuntime.ts';


test('普通浏览器不请求桌面后端配置', async () => {
  assert.equal(await loadDesktopBackendConfig({ location: { protocol: 'https:', hostname: 'finance.example.com' } }), null);
});


test('Tauri 运行时通过受控命令获取动态端口和启动令牌', async () => {
  const calls: string[] = [];
  const config = await loadDesktopBackendConfig({
    location: { protocol: 'tauri:', hostname: 'localhost' },
    __TAURI__: {
      invoke: async <T>(command: string) => {
        calls.push(command);
        return {
          api_base_url: 'http://127.0.0.1:43123/api/v1',
          token: 'per-launch-secret',
        } as T;
      },
    },
  });

  assert.deepEqual(calls, ['desktop_backend_config']);
  assert.deepEqual(config, {
    api_base_url: 'http://127.0.0.1:43123/api/v1',
    token: 'per-launch-secret',
  });
});


test('拒绝非回环地址的桌面后端配置', async () => {
  await assert.rejects(
    loadDesktopBackendConfig({
      location: { protocol: 'tauri:', hostname: 'localhost' },
      __TAURI__: {
        invoke: async <T>() => ({
          api_base_url: 'https://attacker.example.com/api/v1',
          token: 'stolen',
        }) as T,
      },
    }),
    /无效的桌面后端地址/,
  );
});
