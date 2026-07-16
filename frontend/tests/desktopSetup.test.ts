import assert from 'node:assert/strict';
import test from 'node:test';

import {
  desktopInitializationErrorMessage,
  submitDesktopCredentials,
} from '../src/services/desktopSetup.ts';


test('首次桌面初始化先创建管理员再登录', async () => {
  const calls: string[] = [];
  const session = await submitDesktopCredentials({
    setupRequired: true,
    username: 'owner',
    password: 'correct-horse-battery-staple',
    setup: async () => { calls.push('setup'); },
    login: async () => { calls.push('login'); return { access_token: 'token' }; },
  });

  assert.deepEqual(calls, ['setup', 'login']);
  assert.deepEqual(session, { access_token: 'token' });
});


test('已初始化桌面直接登录', async () => {
  const calls: string[] = [];
  await submitDesktopCredentials({
    setupRequired: false,
    username: 'owner',
    password: 'correct-horse-battery-staple',
    setup: async () => { calls.push('setup'); },
    login: async () => { calls.push('login'); return { access_token: 'token' }; },
  });

  assert.deepEqual(calls, ['login']);
});


test('桌面启动超时显示可重试提示', () => {
  assert.equal(
    desktopInitializationErrorMessage(new Error('桌面后端未能在 90 秒内启动')),
    '本地服务启动超时，请重试；若仍失败，请重新启动应用。',
  );
});


test('IPC 不可用显示桌面通信错误', () => {
  assert.equal(
    desktopInitializationErrorMessage(new Error('Tauri IPC 接口不可用')),
    '桌面通信接口不可用，请重新启动应用。',
  );
});
