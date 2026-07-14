export type ImportQueueStatus = 'ready' | 'preflighting' | 'importing' | 'imported' | 'duplicate' | 'attention' | 'failed';

export interface ImportQueueContext {
  businessDate: string;
  profileCode: string;
  storeId: number | null;
}

export interface ImportQueueItem<TFile> {
  key: string;
  file: TFile;
  status: ImportQueueStatus;
  context: ImportQueueContext;
  preflight?: unknown;
  error?: string;
}

export type ImportQueueMap<TFile> = Record<string, ImportQueueItem<TFile>[]>;

const completedStatuses = new Set<ImportQueueStatus>(['imported', 'duplicate', 'attention']);

export const queueKey = (context: ImportQueueContext) =>
  `${context.businessDate}::${context.profileCode}::${context.storeId ?? 'none'}`;

export const getQueue = <TFile>(queues: ImportQueueMap<TFile>, context: ImportQueueContext) =>
  queues[queueKey(context)] ?? [];

export const replaceQueue = <TFile>(queues: ImportQueueMap<TFile>, context: ImportQueueContext, items: ImportQueueItem<TFile>[]) => ({
  ...queues,
  [queueKey(context)]: items,
});

export const clearQueue = <TFile>(queues: ImportQueueMap<TFile>, context: ImportQueueContext) => {
  const next = { ...queues };
  delete next[queueKey(context)];
  return next;
};

export const runnableItems = <TFile>(items: ImportQueueItem<TFile>[]) =>
  items.filter((item) => item.status === 'ready' || item.status === 'failed');

export const createQueueItems = <TFile>(
  files: TFile[],
  context: ImportQueueContext,
  keyForFile: (file: TFile, index: number) => string,
): ImportQueueItem<TFile>[] => files.map((file, index) => ({
  key: keyForFile(file, index),
  file,
  status: 'ready',
  context: { ...context },
}));

export const runWithProcessing = async <T>(
  setProcessing: (processing: boolean) => void,
  operation: () => Promise<T>,
) => {
  setProcessing(true);
  try {
    return await operation();
  } finally {
    setProcessing(false);
  }
};

export const isCurrentImportContext = (context: ImportQueueContext, currentBusinessDate: string) =>
  context.businessDate === currentBusinessDate;

export const prepareQueueItemRetry = <TFile>(item: ImportQueueItem<TFile>) => {
  item.status = 'ready';
  item.error = undefined;
  item.preflight = undefined;
  return item;
};

export const summarizeProfileQueue = <TFile>(queues: ImportQueueMap<TFile>, businessDate: string, profileCode: string) => {
  const items = Object.values(queues).flat().filter(
    (item) => item.context.businessDate === businessDate && item.context.profileCode === profileCode,
  );
  return {
    pending: items.filter((item) => item.status === 'ready').length,
    failed: items.filter((item) => item.status === 'failed').length,
    completed: items.filter((item) => completedStatuses.has(item.status)).length,
  };
};
