import assert from 'node:assert/strict';
import test from 'node:test';

import {
  createDesktopUpdaterController,
  type DesktopUpdaterAdapter,
} from '../src/services/desktopUpdaterController.ts';
import type { DesktopUpdateProgress } from '../src/services/desktopUpdater.ts';

const deferred = <T>() => {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
};

const adapter = (
  overrides: Partial<DesktopUpdaterAdapter> = {},
): DesktopUpdaterAdapter => ({
  supported: async () => true,
  version: async () => '1.0.9',
  check: async () => ({ status: 'up_to_date' }),
  install: async () => undefined,
  errorMessage: () => '更新失败',
  ...overrides,
});

test('初始化只识别平台和版本，不自动检查更新', async () => {
  const calls: string[] = [];
  const controller = createDesktopUpdaterController(adapter({
    check: async () => {
      calls.push('check');
      return { status: 'up_to_date' };
    },
  }));

  await controller.initialize();

  assert.deepEqual(calls, []);
  assert.deepEqual(controller.getState(), {
    phase: 'idle',
    currentVersion: '1.0.9',
  });
});

test('不支持的平台停在 unsupported 且不读取版本', async () => {
  let versionRead = false;
  const controller = createDesktopUpdaterController(adapter({
    supported: async () => false,
    version: async () => {
      versionRead = true;
      return '1.0.9';
    },
  }));

  await controller.initialize();

  assert.deepEqual(controller.getState(), { phase: 'unsupported' });
  assert.equal(versionRead, false);
});

test('检查进行中忽略第二次点击', async () => {
  const result = deferred<{ status: 'up_to_date' }>();
  let calls = 0;
  const controller = createDesktopUpdaterController(adapter({
    check: async () => {
      calls += 1;
      return result.promise;
    },
  }));
  await controller.initialize();

  const first = controller.check();
  const second = controller.check();
  assert.equal(calls, 1);
  assert.equal(controller.getState().phase, 'checking');
  result.resolve({ status: 'up_to_date' });
  await Promise.all([first, second]);

  assert.equal(controller.getState().phase, 'up_to_date');
});

test('发现新版本后关闭弹窗仍保留 available 供侧栏提示', async () => {
  const controller = createDesktopUpdaterController(adapter({
    check: async () => ({
      status: 'available',
      manifest: {
        version: '1.0.10',
        date: '2026-07-17T08:00:00Z',
        body: '修复导入问题',
      },
    }),
  }));
  await controller.initialize();

  await controller.check();
  assert.deepEqual(controller.getState(), {
    phase: 'available',
    currentVersion: '1.0.9',
    manifest: {
      version: '1.0.10',
      date: '2026-07-17T08:00:00Z',
      body: '修复导入问题',
    },
  });
  controller.dismiss();
  assert.deepEqual(controller.getState(), {
    phase: 'available',
    currentVersion: '1.0.9',
    manifest: {
      version: '1.0.10',
      date: '2026-07-17T08:00:00Z',
      body: '修复导入问题',
    },
  });
});

test('下载进度进入 downloading 和 installing 且过程中不可关闭', async () => {
  const installDone = deferred<void>();
  let progressHandler: ((progress: DesktopUpdateProgress) => void) | undefined;
  const controller = createDesktopUpdaterController(adapter({
    check: async () => ({
      status: 'available',
      manifest: { version: '1.0.10', date: '', body: '' },
    }),
    install: async (onProgress) => {
      progressHandler = onProgress;
      return installDone.promise;
    },
  }));
  await controller.initialize();
  await controller.check();

  const installing = controller.install();
  progressHandler?.({
    phase: 'downloading',
    downloadedBytes: 25,
    totalBytes: 100,
    percent: 25,
  });
  assert.deepEqual(controller.getState(), {
    phase: 'downloading',
    currentVersion: '1.0.9',
    manifest: { version: '1.0.10', date: '', body: '' },
    downloadedBytes: 25,
    totalBytes: 100,
    percent: 25,
  });
  controller.dismiss();
  assert.equal(controller.getState().phase, 'downloading');

  progressHandler?.({
    phase: 'installing',
    downloadedBytes: 100,
    totalBytes: 100,
    percent: 100,
  });
  assert.equal(controller.getState().phase, 'installing');
  controller.dismiss();
  assert.equal(controller.getState().phase, 'installing');
  installDone.resolve(undefined);
  await installing;
  assert.equal(controller.getState().phase, 'installing');
});

test('安装失败后重试原安装动作而不重新检查', async () => {
  let checks = 0;
  let installs = 0;
  const controller = createDesktopUpdaterController(adapter({
    check: async () => {
      checks += 1;
      return {
        status: 'available',
        manifest: { version: '1.0.10', date: '', body: '' },
      };
    },
    install: async () => {
      installs += 1;
      if (installs === 1) throw new Error('permission denied');
    },
    errorMessage: () => '无法启动更新安装，请关闭其他程序后重试。',
  }));
  await controller.initialize();
  await controller.check();

  await controller.install();
  assert.deepEqual(controller.getState(), {
    phase: 'error',
    currentVersion: '1.0.9',
    manifest: { version: '1.0.10', date: '', body: '' },
    message: '无法启动更新安装，请关闭其他程序后重试。',
    retryAction: 'install',
  });
  await controller.retry();

  assert.equal(checks, 1);
  assert.equal(installs, 2);
  assert.equal(controller.getState().phase, 'installing');
});

test('订阅者在状态变化时收到更新且可以注销', async () => {
  const phases: string[] = [];
  const controller = createDesktopUpdaterController(adapter());
  const unsubscribe = controller.subscribe((state) => phases.push(state.phase));

  await controller.initialize();
  await controller.check();
  unsubscribe();
  controller.dismiss();

  assert.deepEqual(phases, ['unsupported', 'idle', 'checking', 'up_to_date']);
});
