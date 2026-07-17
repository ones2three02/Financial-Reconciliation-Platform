export interface DesktopBackendConfig {
  api_base_url: string;
  token: string;
}

export type TauriUnlisten = () => void;

export interface TauriUpdaterManifest {
  version: string;
  date?: string;
  body?: string;
}

export interface TauriUpdateResult {
  shouldUpdate: boolean;
  manifest?: TauriUpdaterManifest;
}

export interface TauriUpdaterStatus {
  status: 'PENDING' | 'ERROR' | 'DONE' | 'UPTODATE';
  error?: string;
}

export interface TauriEvent<T> {
  payload: T;
}

export interface TauriBridge {
  invoke<T>(command: string): Promise<T>;
  app?: {
    getVersion(): Promise<string>;
  };
  os?: {
    platform(): Promise<string>;
  };
  updater?: {
    checkUpdate(): Promise<TauriUpdateResult>;
    installUpdate(): Promise<void>;
    onUpdaterEvent(
      handler: (event: TauriUpdaterStatus) => void,
    ): Promise<TauriUnlisten>;
  };
  event?: {
    listen<T>(
      event: string,
      handler: (event: TauriEvent<T>) => void,
    ): Promise<TauriUnlisten>;
  };
  fs?: {
    readBinaryFile(path: string): Promise<Uint8Array>;
  };
}

export interface RuntimeWindow {
  location: {
    protocol: string;
    hostname: string;
  };
  __TAURI__?: TauriBridge;
  __TAURI_METADATA__?: unknown;
}

declare global {
  interface Window {
    __TAURI__?: TauriBridge;
    __TAURI_METADATA__?: unknown;
  }
}

export const isTauriRuntime = (runtime: RuntimeWindow): boolean => (
  runtime.__TAURI__ !== undefined
  || runtime.__TAURI_METADATA__ !== undefined
  || runtime.location.protocol === 'tauri:'
  || runtime.location.hostname === 'tauri.localhost'
);

const validateDesktopBackendConfig = (config: DesktopBackendConfig): DesktopBackendConfig => {
  const url = new URL(config.api_base_url);
  if (
    url.protocol !== 'http:'
    || url.hostname !== '127.0.0.1'
    || url.pathname.replace(/\/$/, '') !== '/api/v1'
    || !url.port
    || config.token.length < 16
  ) {
    throw new Error('无效的桌面后端地址或启动令牌');
  }
  return config;
};

export const loadDesktopBackendConfig = async (
  runtime: RuntimeWindow,
): Promise<DesktopBackendConfig | null> => {
  if (!isTauriRuntime(runtime)) return null;
  if (!runtime.__TAURI__) throw new Error('Tauri IPC 接口不可用');
  const config = await runtime.__TAURI__.invoke<DesktopBackendConfig>('desktop_backend_config');
  return validateDesktopBackendConfig(config);
};
