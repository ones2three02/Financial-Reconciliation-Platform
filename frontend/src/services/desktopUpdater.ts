import {
  isTauriRuntime,
  type RuntimeWindow,
  type TauriBridge,
  type TauriUnlisten,
  type TauriUpdaterManifest,
} from './desktopRuntime.ts';

export interface DesktopUpdateManifest {
  version: string;
  date: string;
  body: string;
}

export type DesktopUpdateCheckResult =
  | { status: 'up_to_date' }
  | { status: 'available'; manifest: DesktopUpdateManifest };

export interface DesktopUpdateProgress {
  phase: 'downloading' | 'installing';
  downloadedBytes: number;
  totalBytes: number | null;
  percent: number | null;
}

export type DesktopUpdaterRuntime = RuntimeWindow;

interface DownloadProgressPayload {
  chunkLength: number;
  contentLength?: number;
}

const requireTauri = (runtime: DesktopUpdaterRuntime): TauriBridge => {
  if (!isTauriRuntime(runtime) || !runtime.__TAURI__) {
    throw new Error('不支持当前运行环境');
  }
  return runtime.__TAURI__;
};

const normalizeManifest = (
  manifest: TauriUpdaterManifest,
): DesktopUpdateManifest => ({
  version: manifest.version.trim(),
  date: manifest.date?.trim() ?? '',
  body: manifest.body?.trim() ?? '',
});

export const isWindowsDesktop = async (
  runtime: DesktopUpdaterRuntime,
): Promise<boolean> => {
  if (!isTauriRuntime(runtime) || !runtime.__TAURI__?.os) return false;
  return (await runtime.__TAURI__.os.platform()) === 'win32';
};

export const getCurrentDesktopVersion = async (
  runtime: DesktopUpdaterRuntime,
): Promise<string> => {
  if (!(await isWindowsDesktop(runtime))) {
    throw new Error('不支持当前运行环境');
  }
  const app = requireTauri(runtime).app;
  if (!app) throw new Error('Tauri 应用版本接口不可用');
  const version = (await app.getVersion()).trim();
  if (!version) throw new Error('桌面应用版本为空');
  return version;
};

export const checkForDesktopUpdate = async (
  runtime: DesktopUpdaterRuntime,
): Promise<DesktopUpdateCheckResult> => {
  if (!(await isWindowsDesktop(runtime))) {
    throw new Error('不支持当前运行环境');
  }
  const updater = requireTauri(runtime).updater;
  if (!updater) throw new Error('Tauri 更新接口不可用');
  const result = await updater.checkUpdate();
  if (!result.shouldUpdate) return { status: 'up_to_date' };
  if (!result.manifest?.version?.trim()) {
    throw new Error('更新清单格式无效');
  }
  return {
    status: 'available',
    manifest: normalizeManifest(result.manifest),
  };
};

export const installDesktopUpdate = async (
  runtime: DesktopUpdaterRuntime,
  onProgress: (progress: DesktopUpdateProgress) => void,
): Promise<void> => {
  if (!(await isWindowsDesktop(runtime))) {
    throw new Error('不支持当前运行环境');
  }
  const tauri = requireTauri(runtime);
  if (!tauri.updater || !tauri.event) {
    throw new Error('Tauri 更新接口不可用');
  }

  let statusUnlisten: TauriUnlisten | undefined;
  let progressUnlisten: TauriUnlisten | undefined;
  let downloadedBytes = 0;
  let totalBytes: number | null = null;
  let rejectStatusError: ((error: Error) => void) | undefined;
  const statusError = new Promise<never>((_resolve, reject) => {
    rejectStatusError = reject;
  });
  void statusError.catch(() => undefined);
  try {
    statusUnlisten = await tauri.updater.onUpdaterEvent(({ error, status }) => {
      if (status === 'ERROR') {
        rejectStatusError?.(new Error(error || '更新安装失败'));
      }
    });
    progressUnlisten = await tauri.event.listen<DownloadProgressPayload>(
      'tauri://update-download-progress',
      ({ payload }) => {
        const chunkLength = Number(payload.chunkLength);
        const contentLength = Number(payload.contentLength);
        if (Number.isFinite(contentLength) && contentLength > 0) {
          totalBytes = contentLength;
        }
        if (Number.isFinite(chunkLength) && chunkLength > 0) {
          downloadedBytes += chunkLength;
        }
        const percent = totalBytes === null
          ? null
          : Math.min(100, Math.round((downloadedBytes / totalBytes) * 100));
        onProgress({
          phase: percent === 100 ? 'installing' : 'downloading',
          downloadedBytes,
          totalBytes,
          percent,
        });
      },
    );
    await Promise.race([tauri.updater.installUpdate(), statusError]);
  } finally {
    progressUnlisten?.();
    statusUnlisten?.();
  }
};

export const desktopUpdateErrorMessage = (error: unknown): string => {
  const message = error instanceof Error ? error.message : String(error ?? '');
  const normalized = message.toLowerCase();
  if (normalized.includes('signature') || normalized.includes('签名')) {
    return '更新包签名验证失败，已取消安装。';
  }
  if (
    normalized.includes('404')
    || normalized.includes('json')
    || normalized.includes('manifest')
    || normalized.includes('清单')
  ) {
    return '更新服务尚未正确发布，请联系维护人员。';
  }
  if (
    normalized.includes('network')
    || normalized.includes('connection')
    || normalized.includes('timeout')
    || normalized.includes('dns')
    || normalized.includes('网络')
  ) {
    return '无法连接更新服务，请检查网络后重试。';
  }
  if (
    normalized.includes('permission')
    || normalized.includes('access denied')
    || normalized.includes('权限')
  ) {
    return '无法启动更新安装，请关闭其他程序后重试。';
  }
  if (normalized.includes('不支持当前运行环境')) {
    return '当前运行环境不支持桌面更新。';
  }
  return '检查或安装更新失败，请稍后重试。';
};
