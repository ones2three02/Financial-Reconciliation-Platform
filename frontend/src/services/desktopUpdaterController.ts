import type {
  DesktopUpdateCheckResult,
  DesktopUpdateManifest,
  DesktopUpdateProgress,
} from './desktopUpdater.ts';

type VersionedPhase = {
  currentVersion: string;
};

export type DesktopUpdaterState =
  | { phase: 'unsupported' }
  | ({ phase: 'idle' | 'checking' | 'up_to_date' } & VersionedPhase)
  | ({ phase: 'available'; manifest: DesktopUpdateManifest } & VersionedPhase)
  | ({
      phase: 'downloading';
      manifest: DesktopUpdateManifest;
      downloadedBytes: number;
      totalBytes: number | null;
      percent: number | null;
    } & VersionedPhase)
  | ({ phase: 'installing'; manifest: DesktopUpdateManifest } & VersionedPhase)
  | ({
      phase: 'error';
      message: string;
      retryAction: 'check' | 'install';
      manifest?: DesktopUpdateManifest;
    } & VersionedPhase);

export interface DesktopUpdaterAdapter {
  supported(): Promise<boolean>;
  version(): Promise<string>;
  check(): Promise<DesktopUpdateCheckResult>;
  install(onProgress: (progress: DesktopUpdateProgress) => void): Promise<void>;
  errorMessage(error: unknown): string;
}

export interface DesktopUpdaterController {
  initialize(): Promise<void>;
  check(): Promise<void>;
  install(): Promise<void>;
  dismiss(): void;
  retry(): Promise<void>;
  getState(): DesktopUpdaterState;
  subscribe(listener: (state: DesktopUpdaterState) => void): () => void;
}

export const createDesktopUpdaterController = (
  adapter: DesktopUpdaterAdapter,
): DesktopUpdaterController => {
  let state: DesktopUpdaterState = { phase: 'unsupported' };
  let activeOperation: Promise<void> | null = null;
  const listeners = new Set<(next: DesktopUpdaterState) => void>();

  const setState = (next: DesktopUpdaterState) => {
    state = next;
    for (const listener of listeners) listener(state);
  };

  const currentVersion = (): string | null => (
    'currentVersion' in state ? state.currentVersion : null
  );

  const initialize = async () => {
    if (!(await adapter.supported())) {
      setState({ phase: 'unsupported' });
      return;
    }
    setState({ phase: 'idle', currentVersion: await adapter.version() });
  };

  const check = (): Promise<void> => {
    if (activeOperation) return activeOperation;
    const version = currentVersion();
    if (version === null) return Promise.resolve();
    const run = (async () => {
      setState({ phase: 'checking', currentVersion: version });
      try {
        const result = await adapter.check();
        if (result.status === 'up_to_date') {
          setState({ phase: 'up_to_date', currentVersion: version });
        } else {
          setState({
            phase: 'available',
            currentVersion: version,
            manifest: result.manifest,
          });
        }
      } catch (error) {
        setState({
          phase: 'error',
          currentVersion: version,
          message: adapter.errorMessage(error),
          retryAction: 'check',
        });
      }
    })();
    activeOperation = run;
    void run.finally(() => {
      if (activeOperation === run) activeOperation = null;
    });
    return run;
  };

  const install = (): Promise<void> => {
    if (activeOperation) return activeOperation;
    const version = currentVersion();
    const manifest = state.phase === 'available'
      ? state.manifest
      : state.phase === 'error' && state.retryAction === 'install'
        ? state.manifest
        : undefined;
    if (version === null || manifest === undefined) return Promise.resolve();

    const run = (async () => {
      setState({
        phase: 'downloading',
        currentVersion: version,
        manifest,
        downloadedBytes: 0,
        totalBytes: null,
        percent: null,
      });
      try {
        await adapter.install((progress) => {
          if (progress.phase === 'installing') {
            setState({
              phase: 'installing',
              currentVersion: version,
              manifest,
            });
            return;
          }
          setState({
            phase: 'downloading',
            currentVersion: version,
            manifest,
            downloadedBytes: progress.downloadedBytes,
            totalBytes: progress.totalBytes,
            percent: progress.percent,
          });
        });
        if (state.phase !== 'installing') {
          setState({
            phase: 'installing',
            currentVersion: version,
            manifest,
          });
        }
      } catch (error) {
        setState({
          phase: 'error',
          currentVersion: version,
          manifest,
          message: adapter.errorMessage(error),
          retryAction: 'install',
        });
      }
    })();
    activeOperation = run;
    void run.finally(() => {
      if (activeOperation === run) activeOperation = null;
    });
    return run;
  };

  const dismiss = () => {
    if (
      state.phase === 'up_to_date'
      || state.phase === 'error'
    ) {
      setState({ phase: 'idle', currentVersion: state.currentVersion });
    }
  };

  const retry = (): Promise<void> => {
    if (state.phase !== 'error') return Promise.resolve();
    return state.retryAction === 'install' ? install() : check();
  };

  return {
    initialize,
    check,
    install,
    dismiss,
    retry,
    getState: () => state,
    subscribe: (listener) => {
      listeners.add(listener);
      listener(state);
      return () => listeners.delete(listener);
    },
  };
};
