import assert from 'node:assert/strict';
import test from 'node:test';

import { submitDesktopCredentials } from '../src/services/desktopSetup.ts';


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
