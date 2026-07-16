import {
  loadDesktopBackendConfig,
  type DesktopBackendConfig,
  type RuntimeWindow,
} from './desktopRuntime.ts';

type DesktopConfigLoader = (runtime: RuntimeWindow) => Promise<DesktopBackendConfig | null>;

export const createDesktopConnection = (load: DesktopConfigLoader = loadDesktopBackendConfig) => {
  let cached: DesktopBackendConfig | null | undefined;
  let pending: Promise<DesktopBackendConfig | null> | null = null;

  return {
    async get(runtime: RuntimeWindow) {
      if (cached !== undefined) return cached;
      if (!pending) {
        pending = load(runtime)
          .then((config) => {
            cached = config;
            return config;
          })
          .finally(() => { pending = null; });
      }
      return pending;
    },
    reset() {
      cached = undefined;
      pending = null;
    },
  };
};

const desktopConnection = createDesktopConnection();

export const getDesktopBackendConfig = (runtime: RuntimeWindow) => desktopConnection.get(runtime);
export const resetDesktopBackendConnection = () => desktopConnection.reset();
