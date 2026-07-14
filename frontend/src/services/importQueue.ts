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
