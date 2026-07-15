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
