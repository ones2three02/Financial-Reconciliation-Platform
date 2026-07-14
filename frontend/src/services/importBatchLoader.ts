interface BatchReference {
  id: number;
  business_date: string;
}

interface LoadExistingBatchOptions<TBatch extends BatchReference, TDetail> {
  requestedBusinessDate: string;
  getCurrentBusinessDate: () => string;
  getBatches: () => Promise<TBatch[]>;
  getBatchDetail: (batchId: number) => Promise<TDetail>;
}

export interface ExistingBatchLoad<TBatch, TDetail> {
  batch: TBatch | null;
  detail: TDetail | null;
}

export const loadExistingBatchForDate = async <TBatch extends BatchReference, TDetail>({
  requestedBusinessDate,
  getCurrentBusinessDate,
  getBatches,
  getBatchDetail,
}: LoadExistingBatchOptions<TBatch, TDetail>): Promise<ExistingBatchLoad<TBatch, TDetail> | null> => {
  const batches = await getBatches();
  if (getCurrentBusinessDate() !== requestedBusinessDate) return null;

  const batch = batches.find((item) => item.business_date === requestedBusinessDate) ?? null;
  if (!batch) return { batch: null, detail: null };

  const detail = await getBatchDetail(batch.id);
  if (getCurrentBusinessDate() !== requestedBusinessDate) return null;
  return { batch, detail };
};
