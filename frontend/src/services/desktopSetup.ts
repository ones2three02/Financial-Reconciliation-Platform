interface SubmitDesktopCredentialsOptions<T> {
  setupRequired: boolean;
  username: string;
  password: string;
  setup(username: string, password: string): Promise<unknown>;
  login(username: string, password: string): Promise<T>;
}

export const submitDesktopCredentials = async <T>(
  options: SubmitDesktopCredentialsOptions<T>,
): Promise<T> => {
  if (options.setupRequired) {
    await options.setup(options.username, options.password);
  }
  return options.login(options.username, options.password);
};

export const desktopInitializationErrorMessage = (error: unknown): string => {
  const message = error instanceof Error ? error.message : String(error ?? '');
  if (message.includes('90 秒') || message.includes('TimedOut') || message.includes('超时')) {
    return '本地服务启动超时，请重试；若仍失败，请重新启动应用。';
  }
  if (message.includes('IPC') || message.includes('Tauri')) {
    return '桌面通信接口不可用，请重新启动应用。';
  }
  if (message.includes('无效的桌面后端')) {
    return '桌面服务配置无效，请重新启动应用。';
  }
  return '桌面服务初始化失败，请重试；若仍失败，请重新启动应用。';
};
