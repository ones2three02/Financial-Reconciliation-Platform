import assert from 'node:assert/strict';
import test from 'node:test';

import {
  checkForDesktopUpdate,
  desktopUpdateErrorMessage,
  getCurrentDesktopVersion,
  installDesktopUpdate,
  isWindowsDesktop,
  type DesktopUpdaterRuntime,
} from '../src/services/desktopUpdater.ts';

type TestRuntime = DesktopUpdaterRuntime & {
  __TAURI__: NonNullable<DesktopUpdaterRuntime['__TAURI__']>;
};

const runtime = (platform: string, shouldUpdate = false): TestRuntime => ({
  location: { protocol: 'https:', hostname: 'tauri.localhost' },
  __TAURI__: {
    invoke: async <T>() => undefined as T,
    app: { getVersion: async () => '1.0.9' },
    os: { platform: async () => platform },
    updater: {
      checkUpdate: async () => shouldUpdate
        ? {
            shouldUpdate: true,
            manifest: {
              version: '1.0.10',
              date: '2026-07-17T08:00:00Z',
              body: '修复导入问题',
            },
          }
        : { shouldUpdate: false },
      installUpdate: async () => undefined,
      onUpdaterEvent: async () => () => undefined,
    },
    event: { listen: async () => () => undefined },
  },
});

test('只有 Windows Tauri 环境支持桌面更新', async () => {
  assert.equal(await isWindowsDesktop(runtime('win32')), true);
  assert.equal(await isWindowsDesktop(runtime('darwin')), false);
  assert.equal(
    await isWindowsDesktop({
      location: { protocol: 'https:', hostname: 'finance.example.com' },
    }),
    false,
  );
});

test('读取实际运行版本且检查动作返回稳定业务结果', async () => {
  assert.equal(await getCurrentDesktopVersion(runtime('win32')), '1.0.9');
  assert.deepEqual(await checkForDesktopUpdate(runtime('win32', true)), {
    status: 'available',
    manifest: {
      version: '1.0.10',
      date: '2026-07-17T08:00:00Z',
      body: '修复导入问题',
    },
  });
  assert.deepEqual(await checkForDesktopUpdate(runtime('win32')), {
    status: 'up_to_date',
  });
});

test('非 Windows 环境不会调用检查更新 API', async () => {
  let checked = false;
  const mac = runtime('darwin');
  mac.__TAURI__.updater!.checkUpdate = async () => {
    checked = true;
    return { shouldUpdate: false };
  };

  await assert.rejects(checkForDesktopUpdate(mac), /不支持当前运行环境/);
  assert.equal(checked, false);
});

test('安装过程上报下载与安装阶段并在成功后注销监听器', async () => {
  const cleanup: string[] = [];
  const phases: string[] = [];
  const percentages: Array<number | null> = [];
  const win = runtime('win32');
  win.__TAURI__.updater!.onUpdaterEvent = async (handler) => {
    handler({ status: 'PENDING' });
    return () => { cleanup.push('status'); };
  };
  win.__TAURI__.event!.listen = async (_name, handler) => {
    handler({ payload: { chunkLength: 25, contentLength: 100 } });
    handler({ payload: { chunkLength: 75, contentLength: 100 } });
    return () => { cleanup.push('progress'); };
  };

  await installDesktopUpdate(win, (event) => {
    phases.push(event.phase);
    percentages.push(event.percent);
  });

  assert.deepEqual(phases, ['downloading', 'installing']);
  assert.deepEqual(percentages, [25, 100]);
  assert.deepEqual(cleanup.sort(), ['progress', 'status']);
});

test('安装失败同样注销监听器', async () => {
  const cleanup: string[] = [];
  const win = runtime('win32');
  win.__TAURI__.updater!.onUpdaterEvent = async () => (
    () => { cleanup.push('status'); }
  );
  win.__TAURI__.event!.listen = async () => (
    () => { cleanup.push('progress'); }
  );
  win.__TAURI__.updater!.installUpdate = async () => {
    throw new Error('download failed');
  };

  await assert.rejects(
    installDesktopUpdate(win, () => undefined),
    /download failed/,
  );
  assert.deepEqual(cleanup.sort(), ['progress', 'status']);
});

test('更新器状态事件报错会中止安装并注销监听器', async () => {
  const cleanup: string[] = [];
  const win = runtime('win32');
  let statusHandler: ((event: { status: 'ERROR'; error: string }) => void) | undefined;
  win.__TAURI__.updater!.onUpdaterEvent = async (handler) => {
    statusHandler = handler;
    return () => { cleanup.push('status'); };
  };
  win.__TAURI__.event!.listen = async () => (
    () => { cleanup.push('progress'); }
  );
  win.__TAURI__.updater!.installUpdate = async () => {
    queueMicrotask(() => statusHandler?.({ status: 'ERROR', error: 'signature failed' }));
    await new Promise((resolve) => setTimeout(resolve, 20));
  };

  await assert.rejects(
    installDesktopUpdate(win, () => undefined),
    /signature failed/,
  );
  assert.deepEqual(cleanup.sort(), ['progress', 'status']);
});

test('更新错误转换为不泄露内部信息的中文提示', () => {
  assert.equal(
    desktopUpdateErrorMessage(new Error('signature verification failed')),
    '更新包签名验证失败，已取消安装。',
  );
  assert.equal(
    desktopUpdateErrorMessage(new Error('404 latest.json invalid JSON')),
    '更新服务尚未正确发布，请联系维护人员。',
  );
  assert.equal(
    desktopUpdateErrorMessage(new Error('network connection timeout')),
    '无法连接更新服务，请检查网络后重试。',
  );
  assert.equal(
    desktopUpdateErrorMessage(new Error('permission denied')),
    '无法启动更新安装，请关闭其他程序后重试。',
  );
});
