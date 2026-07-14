<template>
  <div class="space-y-6 fade-in">
    <Card class="border-slate-200/80 shadow-sm">
      <CardHeader class="flex flex-row items-start justify-between gap-4">
        <div>
          <CardTitle class="flex items-center gap-2 text-base">
            <CalendarRange class="h-5 w-5 text-blue-600" />每日对账批次
          </CardTitle>
          <CardDescription>先确认账期，再按来源批量预检和导入。相同文件名允许重复使用，系统按内容和业务范围判重。</CardDescription>
        </div>
        <div class="flex items-center gap-3">
          <span v-if="activeBatch" :class="batchStatusClass(activeBatch.status)" class="rounded-full px-3 py-1 text-xs font-bold">
            {{ batchStatusLabel(activeBatch.status) }} · V{{ activeBatch.version }}
          </span>
          <Button variant="outline" size="sm" :disabled="loadingBatch || !canOperate" @click="ensureBatch">
            {{ loadingBatch ? '载入中...' : activeBatch ? '刷新批次' : '创建该账期批次' }}
          </Button>
          <Button v-if="activeBatch && activeBatch.status !== 'closed' && canOperate" variant="outline" size="sm" class="border-rose-200 text-rose-700" :disabled="processing" @click="openReset">
            <RotateCcw class="mr-1 h-3.5 w-3.5" />重置当日数据
          </Button>
          <Button v-if="batchDetail?.can_restore_last_reset && canOperate" variant="outline" size="sm" class="border-amber-300 text-amber-700" :disabled="processing" @click="openRestoreReset">
            <History class="mr-1 h-3.5 w-3.5" />恢复上次重置
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div class="grid gap-4 md:grid-cols-3">
          <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <div class="text-[10px] font-bold uppercase tracking-wider text-slate-400">当前账期</div>
            <div class="mt-1 text-lg font-extrabold text-slate-800">{{ globalDate }}</div>
          </div>
          <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <div class="text-[10px] font-bold uppercase tracking-wider text-slate-400">已导入文件</div>
            <div class="mt-1 text-lg font-extrabold text-slate-800">{{ currentFileCount }} 份</div>
            <div v-if="historicalFileCount" class="mt-1 text-[10px] text-slate-400">另有 {{ historicalFileCount }} 个历史版本</div>
          </div>
          <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <div class="text-[10px] font-bold uppercase tracking-wider text-slate-400">待处理质量问题</div>
            <div class="mt-1 text-lg font-extrabold" :class="openIssueCount ? 'text-amber-600' : 'text-emerald-600'">{{ openIssueCount }} 项</div>
          </div>
        </div>
      </CardContent>
    </Card>

    <div class="grid gap-6 lg:grid-cols-3">
      <Card class="border-slate-200/80 shadow-sm">
        <CardHeader>
          <CardTitle class="flex items-center gap-2 text-base"><Sliders class="h-4 w-4 text-blue-600" />1. 选择工作簿模板</CardTitle>
          <CardDescription>模板是有版本的白名单规则，不会根据相似表头随意猜测。</CardDescription>
        </CardHeader>
        <CardContent class="space-y-3">
          <label v-for="profile in profiles" :key="profile.code" class="block cursor-pointer rounded-xl border p-3 transition-colors" :class="selectedProfile === profile.code ? 'border-blue-500 bg-blue-50/40' : 'border-slate-200 hover:bg-slate-50'">
            <div class="flex items-start gap-3">
              <input v-model="selectedProfile" type="radio" :value="profile.code" class="mt-1" />
              <div>
                <div class="text-xs font-bold text-slate-800">{{ profile.label }}</div>
                <div class="mt-1 text-[11px] leading-5 text-slate-500">{{ profile.description }}</div>
              </div>
            </div>
          </label>
          <div v-if="selectedProfile === 'store_finance_v1'" class="border-t border-slate-100 pt-3">
            <label class="mb-1.5 block text-[10px] font-bold uppercase tracking-wider text-slate-400">财务表所属门店</label>
            <Select v-model="selectedStoreId" :options="activeStores.map((store) => ({ value: store.id, label: store.name }))" placeholder="必须选择标准门店" />
          </div>
        </CardContent>
      </Card>

      <Card class="border-slate-200/80 shadow-sm lg:col-span-2">
        <CardHeader>
          <CardTitle class="flex items-center gap-2 text-base"><UploadCloud class="h-4 w-4 text-blue-600" />2. 选择并导入文件</CardTitle>
          <CardDescription>支持一次选择多份 .xlsx。每个文件都会先预检，预检通过后才写入批次。</CardDescription>
        </CardHeader>
        <CardContent class="space-y-4">
          <label class="flex min-h-36 cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-200 bg-slate-50/60 p-6 text-center hover:border-blue-400">
            <FileSpreadsheet class="mb-2 h-9 w-9 text-emerald-600" />
            <span class="text-sm font-bold text-slate-700">选择一份或多份 Excel 工作簿</span>
            <span class="mt-1 text-xs text-slate-400">仅支持 .xlsx；单文件大小与解压规模均受安全限制</span>
            <input type="file" accept=".xlsx" multiple class="hidden" @change="onFilesSelected" />
          </label>

          <div v-if="queue.length" class="space-y-2">
            <div v-for="item in queue" :key="item.key" class="rounded-xl border border-slate-200 bg-white p-3">
              <div class="flex items-center justify-between gap-3">
                <div class="min-w-0">
                  <div class="truncate text-xs font-bold text-slate-700">{{ item.file.name }}</div>
                  <div v-if="item.preflight" class="mt-1 text-[11px] text-slate-500">
                    {{ item.preflight.sheet_name }} · 命中 {{ item.preflight.matching_row_count }}/{{ item.preflight.total_data_rows }} 行 · 输出 {{ item.preflight.output_sources.map(sourceLabel).join('、') }}
                  </div>
                  <div v-if="item.error" class="mt-1 text-[11px] text-rose-600">{{ item.error }}</div>
                </div>
                <span class="shrink-0 rounded-full px-2.5 py-1 text-[10px] font-bold" :class="queueStatusClass(item.status)">{{ queueStatusLabel(item.status) }}</span>
              </div>
            </div>
          </div>

          <div v-if="message" class="rounded-xl border px-4 py-3 text-xs font-semibold" :class="message.type === 'error' ? 'border-rose-200 bg-rose-50 text-rose-700' : 'border-emerald-200 bg-emerald-50 text-emerald-700'">
            {{ message.text }}
          </div>

          <div class="flex justify-end gap-3">
            <Button variant="outline" :disabled="processing || !queue.length" @click="queue = []">清空列表</Button>
            <Button class="bg-blue-600 text-white hover:bg-blue-700" :disabled="processing || !canImport" @click="processQueue">
              {{ processing ? '正在逐份预检并导入...' : `开始导入 ${queue.length} 份文件` }}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>

    <Card class="border-slate-200/80 shadow-sm">
      <CardHeader class="flex flex-row items-start justify-between gap-4">
        <div>
          <CardTitle class="flex items-center gap-2 text-base"><History class="h-4 w-4 text-blue-600" />当前批次导入记录</CardTitle>
          <CardDescription>“追加”使用上方普通导入；导错时请选择原文件进行替换或作废，系统不会物理删除历史。</CardDescription>
        </div>
        <Button v-if="historicalFileCount" variant="outline" size="sm" @click="showHistory = !showHistory">
          {{ showHistory ? '隐藏历史版本' : `显示历史版本（${historicalFileCount}）` }}
        </Button>
      </CardHeader>
      <CardContent class="p-0">
        <div class="overflow-x-auto border-t border-slate-100">
          <table class="w-full text-left text-xs">
            <thead class="bg-slate-50 text-[10px] uppercase tracking-wider text-slate-400">
              <tr><th class="p-4">文件</th><th class="p-4">模板</th><th class="p-4">来源</th><th class="p-4">行数</th><th class="p-4">版本</th><th class="p-4">处理状态</th><th class="p-4">导入时间</th><th class="p-4 text-right">操作</th></tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <tr v-if="!visibleImportFiles.length"><td colspan="8" class="p-8 text-center text-slate-400">该账期尚未导入文件</td></tr>
              <tr v-for="file in visibleImportFiles" :key="file.id" :class="file.is_current ? '' : 'bg-slate-50/70 opacity-75'">
                <td class="p-4">
                  <div class="font-bold text-slate-700">{{ file.filename }}</div>
                  <div class="mt-1 font-mono text-[10px] text-slate-400">文件 #{{ file.id }}<span v-if="file.supersedes_file_id"> · 替换 #{{ file.supersedes_file_id }}</span></div>
                </td>
                <td class="p-4 text-slate-500">{{ profileLabel(file.profile_code) }}</td>
                <td class="p-4 text-slate-500">{{ sourceLabel(file.data_source) }}</td>
                <td class="p-4 text-slate-500">{{ file.row_count }}</td>
                <td class="p-4"><span class="rounded-full px-2 py-1 font-bold" :class="file.is_current ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-200 text-slate-600'">{{ file.is_current ? '当前有效' : '历史版本' }}</span></td>
                <td class="p-4"><span class="rounded-full bg-slate-100 px-2 py-1 font-bold text-slate-600">{{ file.upload_status }}</span></td>
                <td class="p-4 font-mono text-slate-500">{{ formatDateTime(file.uploaded_at) }}</td>
                <td class="p-4 text-right">
                  <div v-if="file.is_current && activeBatch?.status !== 'closed' && canOperate" class="flex justify-end gap-2">
                    <Button variant="outline" size="xs" :disabled="processing" @click="openFileAction('replace', file)"><RefreshCw class="mr-1 h-3 w-3" />替换</Button>
                    <Button variant="outline" size="xs" class="border-rose-200 text-rose-700" :disabled="processing" @click="openFileAction('invalidate', file)"><Ban class="mr-1 h-3 w-3" />作废</Button>
                  </div>
                  <Button v-else-if="!file.is_current && activeBatch?.status !== 'closed' && canOperate" variant="outline" size="xs" class="border-amber-300 text-amber-700" :disabled="processing" @click="openFileAction('restore', file)"><RotateCcw class="mr-1 h-3 w-3" />恢复为当前版本</Button>
                  <span v-else class="text-slate-300">—</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>

    <div v-if="actionFile" class="fixed inset-0 z-50 flex items-center justify-center bg-zinc-950/40 p-4 backdrop-blur-sm" @click.self="closeFileAction">
      <Card class="w-full max-w-lg bg-white shadow-2xl">
        <CardHeader>
          <CardTitle class="text-base">{{ fileAction === 'replace' ? '替换导入文件' : fileAction === 'invalidate' ? '作废导入文件' : '恢复历史导入文件' }}</CardTitle>
          <CardDescription v-if="fileAction === 'replace'">将以新文件替换“{{ actionFile.filename }}”，沿用原账期、模板和文件级门店。渠道表按整份文件替换。</CardDescription>
          <CardDescription v-else-if="fileAction === 'invalidate'">“{{ actionFile.filename }}”将退出当前对账，但原文件、原始数据和历史版本仍永久保留。</CardDescription>
          <CardDescription v-else>系统将从“{{ actionFile.filename }}”保留的原始数据创建新的提取运行，并自动重新对账；同一版本链的当前替代文件将退出计算。</CardDescription>
        </CardHeader>
        <CardContent class="space-y-4">
          <label v-if="fileAction === 'replace'" class="block rounded-xl border-2 border-dashed border-slate-200 bg-slate-50 p-4 text-center text-xs font-bold text-slate-600">
            {{ replacementFile?.name ?? '选择正确的 .xlsx 文件' }}
            <input type="file" accept=".xlsx" class="hidden" @change="onReplacementSelected" />
          </label>
          <div v-if="fileAction === 'restore'" class="grid grid-cols-[88px_1fr] gap-2 rounded-xl bg-slate-50 p-4 text-xs">
            <span class="text-slate-500">原模板</span><strong>{{ profileLabel(actionFile.profile_code) }}</strong>
            <span class="text-slate-500">数据来源</span><strong>{{ sourceLabel(actionFile.data_source) }}</strong>
            <span class="text-slate-500">门店范围</span><strong>{{ fileStoreName(actionFile) }}</strong>
          </div>
          <textarea v-model="actionReason" rows="4" maxlength="500" class="w-full rounded-xl border border-slate-200 p-3 text-sm outline-none focus:ring-2 focus:ring-blue-500" :placeholder="fileAction === 'replace' ? '请输入替换原因，例如：原文件导出日期范围错误' : fileAction === 'invalidate' ? '请输入作废原因，例如：误传了其他账期文件' : '请输入恢复原因，例如：刚才误作废了正确文件'"></textarea>
          <div class="rounded-lg bg-amber-50 p-3 text-[11px] leading-5 text-amber-800">操作完成后会立即重算覆盖状态和对账结果。已关账批次必须先重开。</div>
        </CardContent>
        <CardFooter class="justify-end gap-3"><Button variant="outline" @click="closeFileAction">取消</Button><Button :class="fileAction === 'invalidate' ? 'bg-rose-600 text-white hover:bg-rose-700' : fileAction === 'restore' ? 'bg-amber-600 text-white hover:bg-amber-700' : ''" :disabled="processing || !actionReason.trim() || (fileAction === 'replace' && !replacementFile)" @click="submitFileAction">{{ processing ? '处理中...' : '确认执行' }}</Button></CardFooter>
      </Card>
    </div>

    <div v-if="showReset" class="fixed inset-0 z-50 flex items-center justify-center bg-zinc-950/40 p-4 backdrop-blur-sm" @click.self="closeReset">
      <Card class="w-full max-w-lg bg-white shadow-2xl">
        <CardHeader><CardTitle class="text-base text-rose-700">重置 {{ globalDate }} 当日当前数据</CardTitle><CardDescription>所有当前文件和人工确认零收入将退出当前计算，历史数据不会删除。完成后需要重新导入。</CardDescription></CardHeader>
        <CardContent class="space-y-4">
          <textarea v-model="resetReason" rows="4" maxlength="500" class="w-full rounded-xl border border-slate-200 p-3 text-sm outline-none focus:ring-2 focus:ring-rose-500" placeholder="请输入整批重置原因"></textarea>
          <div><label class="mb-1.5 block text-xs font-bold text-slate-700">再次输入账期日期确认</label><input v-model="resetConfirmationDate" type="text" class="w-full rounded-xl border border-slate-200 p-3 font-mono text-sm outline-none focus:ring-2 focus:ring-rose-500" :placeholder="globalDate" /></div>
          <label class="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs font-semibold text-rose-800"><input v-model="resetRiskAcknowledged" type="checkbox" class="mt-0.5" /><span>我已确认账期为 {{ globalDate }}，并了解所有当前文件、人工确认零和当前对账结果都会退出计算。</span></label>
        </CardContent>
        <CardFooter class="justify-end gap-3"><Button variant="outline" @click="closeReset">取消</Button><Button class="bg-rose-600 text-white hover:bg-rose-700" :disabled="processing || !resetReason.trim() || resetConfirmationDate !== globalDate || !resetRiskAcknowledged" @click="submitReset">{{ processing ? '重置中...' : '确认重置当前数据' }}</Button></CardFooter>
      </Card>
    </div>

    <div v-if="showRestoreReset" class="fixed inset-0 z-50 flex items-center justify-center bg-zinc-950/40 p-4 backdrop-blur-sm" @click.self="closeRestoreReset">
      <Card class="w-full max-w-lg bg-white shadow-2xl">
        <CardHeader><CardTitle class="text-base text-amber-700">恢复 {{ globalDate }} 上一次整批重置</CardTitle><CardDescription>仅当重置后没有新导入、没有新的零收入确认且批次未关账时可恢复。系统会从原始数据重新提取，而不是直接复活旧计算结果。</CardDescription></CardHeader>
        <CardContent class="space-y-4">
          <textarea v-model="restoreResetReason" rows="4" maxlength="500" class="w-full rounded-xl border border-slate-200 p-3 text-sm outline-none focus:ring-2 focus:ring-amber-500" placeholder="请输入恢复原因，例如：刚才误点了整批重置"></textarea>
          <div><label class="mb-1.5 block text-xs font-bold text-slate-700">再次输入账期日期确认</label><input v-model="restoreResetConfirmationDate" type="text" class="w-full rounded-xl border border-slate-200 p-3 font-mono text-sm outline-none focus:ring-2 focus:ring-amber-500" :placeholder="globalDate" /></div>
          <label class="flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs font-semibold text-amber-800"><input v-model="restoreResetRiskAcknowledged" type="checkbox" class="mt-0.5" /><span>我已核对账期，并了解恢复会重新提取快照文件、恢复当时的人工零收入确认并自动重新对账。</span></label>
        </CardContent>
        <CardFooter class="justify-end gap-3"><Button variant="outline" @click="closeRestoreReset">取消</Button><Button class="bg-amber-600 text-white hover:bg-amber-700" :disabled="processing || !restoreResetReason.trim() || restoreResetConfirmationDate !== globalDate || !restoreResetRiskAcknowledged" @click="submitRestoreReset">{{ processing ? '恢复中...' : '确认恢复上次重置' }}</Button></CardFooter>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { Ban, CalendarRange, FileSpreadsheet, History, RefreshCw, RotateCcw, Sliders, UploadCloud } from 'lucide-vue-next';
import { api, getSession } from '../services/api';
import type { BatchDetail, ImportFile, PreflightResult, ProfileCode, ReconciliationBatch, Store } from '../services/api';
import { globalDate } from '../services/store';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '../components/ui/card';
import { Select } from '../components/ui/select';

type QueueStatus = 'ready' | 'preflighting' | 'importing' | 'imported' | 'duplicate' | 'attention' | 'failed';
interface QueueItem { key: string; file: File; status: QueueStatus; preflight?: PreflightResult; error?: string }

const profiles: { code: ProfileCode; label: string; description: string }[] = [
  { code: 'store_finance_v1', label: '门店财务表', description: '一次导入，同时生成销售收入和现金收入；必须指定标准门店。' },
  { code: 'tonglian_v1', label: '通联好老板', description: '统计成功交易金额，工作簿内门店名称必须经过来源别名确认。' },
  { code: 'meituan_v1', label: '美团收入', description: '按验券/退款日期统计“总收入 + 商家营销费用”。' },
  { code: 'douyin_v1', label: '抖音收入', description: '按核销时间统计订单实收，不引入不存在的撤销核销规则。' },
];

const selectedProfile = ref<ProfileCode>('store_finance_v1');
const selectedStoreId = ref<number | null>(null);
const stores = ref<Store[]>([]);
const activeBatch = ref<ReconciliationBatch | null>(null);
const batchDetail = ref<BatchDetail | null>(null);
const queue = ref<QueueItem[]>([]);
const loadingBatch = ref(false);
const processing = ref(false);
const message = ref<{ type: 'success' | 'error'; text: string } | null>(null);
const showHistory = ref(false);
const actionFile = ref<ImportFile | null>(null);
const fileAction = ref<'replace' | 'invalidate' | 'restore'>('replace');
const actionReason = ref('');
const replacementFile = ref<File | null>(null);
const showReset = ref(false);
const resetReason = ref('');
const resetConfirmationDate = ref('');
const resetRiskAcknowledged = ref(false);
const showRestoreReset = ref(false);
const restoreResetReason = ref('');
const restoreResetConfirmationDate = ref('');
const restoreResetRiskAcknowledged = ref(false);

const activeStores = computed(() => stores.value.filter((store) => store.is_active));
const canOperate = computed(() => ['admin', 'finance'].includes(getSession().role ?? ''));
const openIssueCount = computed(() => batchDetail.value?.quality_issues.filter((issue) => issue.status === 'open').length ?? 0);
const currentFileCount = computed(() => batchDetail.value?.import_files.filter((file) => file.is_current).length ?? 0);
const historicalFileCount = computed(() => batchDetail.value?.import_files.filter((file) => !file.is_current).length ?? 0);
const visibleImportFiles = computed(() => (batchDetail.value?.import_files ?? []).filter((file) => showHistory.value || file.is_current));
const canImport = computed(() => Boolean(
  activeBatch.value
  && canOperate.value
  && activeBatch.value.status !== 'closed'
  && queue.value.length
  && (selectedProfile.value !== 'store_finance_v1' || selectedStoreId.value),
));

const ensureBatch = async () => {
  loadingBatch.value = true;
  message.value = null;
  try {
    activeBatch.value = await api.createBatch(globalDate.value);
    batchDetail.value = await api.getBatchDetail(activeBatch.value.id);
  } catch (error) {
    message.value = { type: 'error', text: errorDetail(error) };
  } finally {
    loadingBatch.value = false;
  }
};

const loadExistingBatch = async () => {
  loadingBatch.value = true;
  try {
    const batch = (await api.getBatches()).find((item) => item.business_date === globalDate.value) ?? null;
    activeBatch.value = batch;
    batchDetail.value = batch ? await api.getBatchDetail(batch.id) : null;
  } finally {
    loadingBatch.value = false;
  }
};

const onFilesSelected = (event: Event) => {
  const input = event.target as HTMLInputElement;
  const files = Array.from(input.files ?? []);
  queue.value = files.map((file, index) => ({ key: `${file.name}-${file.size}-${index}`, file, status: 'ready' }));
  input.value = '';
  message.value = null;
};

const processQueue = async () => {
  if (!activeBatch.value || !canImport.value) return;
  processing.value = true;
  message.value = null;
  let failed = 0;
  for (const item of queue.value) {
    item.error = undefined;
    try {
      item.status = 'preflighting';
      item.preflight = await api.preflightWorkbook(item.file, selectedProfile.value, globalDate.value, selectedStoreId.value);
      item.status = 'importing';
      const outcome = await api.importWorkbook(item.file, activeBatch.value.id, selectedProfile.value, selectedStoreId.value);
      item.status = outcome.status === 'duplicate' ? 'duplicate' : outcome.status === 'attention_required' ? 'attention' : 'imported';
    } catch (error) {
      item.status = 'failed';
      item.error = errorDetail(error);
      failed += 1;
    }
  }
  batchDetail.value = await api.getBatchDetail(activeBatch.value.id);
  activeBatch.value = batchDetail.value.batch;
  message.value = failed
    ? { type: 'error', text: `${queue.value.length - failed} 份导入完成，${failed} 份失败，请查看逐文件原因。` }
    : { type: 'success', text: '本次文件已完成预检和导入。若出现未知门店，请到“对账明细”人工确认。' };
  processing.value = false;
};

const refreshBatch = async () => {
  if (!activeBatch.value) return;
  batchDetail.value = await api.getBatchDetail(activeBatch.value.id);
  activeBatch.value = batchDetail.value.batch;
};

const openFileAction = (action: 'replace' | 'invalidate' | 'restore', file: ImportFile) => {
  fileAction.value = action;
  actionFile.value = file;
  actionReason.value = '';
  replacementFile.value = null;
  message.value = null;
};

const closeFileAction = () => {
  if (processing.value) return;
  actionFile.value = null;
  actionReason.value = '';
  replacementFile.value = null;
};

const onReplacementSelected = (event: Event) => {
  const input = event.target as HTMLInputElement;
  replacementFile.value = input.files?.[0] ?? null;
  input.value = '';
};

const submitFileAction = async () => {
  if (!actionFile.value || !actionReason.value.trim()) return;
  processing.value = true;
  message.value = null;
  try {
    const filename = actionFile.value.filename;
    if (fileAction.value === 'replace') {
      if (!replacementFile.value) return;
      await api.replaceImportFile(actionFile.value.id, replacementFile.value, actionReason.value.trim());
      message.value = { type: 'success', text: `已用新文件替换“${filename}”，覆盖状态和对账结果已自动重算。` };
    } else if (fileAction.value === 'invalidate') {
      await api.invalidateImportFile(actionFile.value.id, actionReason.value.trim());
      message.value = { type: 'success', text: `已作废“${filename}”，历史数据仍然保留。` };
    } else {
      await api.restoreImportFile(actionFile.value.id, actionReason.value.trim());
      message.value = { type: 'success', text: `已将“${filename}”恢复为当前版本，并从原始数据重新提取和对账。` };
    }
    actionFile.value = null;
    actionReason.value = '';
    replacementFile.value = null;
    await refreshBatch();
  } catch (error) {
    message.value = { type: 'error', text: errorDetail(error) };
  } finally {
    processing.value = false;
  }
};

const openReset = () => {
  showReset.value = true;
  resetReason.value = '';
  resetConfirmationDate.value = '';
  resetRiskAcknowledged.value = false;
  message.value = null;
};

const closeReset = () => {
  if (processing.value) return;
  showReset.value = false;
};

const submitReset = async () => {
  if (!activeBatch.value || !resetReason.value.trim() || resetConfirmationDate.value !== globalDate.value || !resetRiskAcknowledged.value) return;
  processing.value = true;
  try {
    activeBatch.value = await api.resetBatchCurrentData(activeBatch.value.id, resetReason.value.trim(), resetConfirmationDate.value, true);
    await refreshBatch();
    showReset.value = false;
    showHistory.value = true;
    message.value = { type: 'success', text: '该账期当前数据已重置，历史仍保留。在导入或确认新数据前，可以使用“恢复上次重置”。' };
  } catch (error) {
    message.value = { type: 'error', text: errorDetail(error) };
  } finally {
    processing.value = false;
  }
};

const openRestoreReset = () => {
  showRestoreReset.value = true;
  restoreResetReason.value = '';
  restoreResetConfirmationDate.value = '';
  restoreResetRiskAcknowledged.value = false;
  message.value = null;
};

const closeRestoreReset = () => {
  if (processing.value) return;
  showRestoreReset.value = false;
};

const submitRestoreReset = async () => {
  if (
    !activeBatch.value
    || !restoreResetReason.value.trim()
    || restoreResetConfirmationDate.value !== globalDate.value
    || !restoreResetRiskAcknowledged.value
  ) return;
  processing.value = true;
  try {
    activeBatch.value = await api.restoreLastReset(
      activeBatch.value.id,
      restoreResetReason.value.trim(),
      restoreResetConfirmationDate.value,
      true,
    );
    await refreshBatch();
    showRestoreReset.value = false;
    message.value = { type: 'success', text: '上一次整批重置已恢复，文件已从原始数据重新提取并自动对账。' };
  } catch (error) {
    message.value = { type: 'error', text: errorDetail(error) };
  } finally {
    processing.value = false;
  }
};

const sourceLabel = (source: string) => ({ tonglian: '通联', meituan: '美团', douyin: '抖音', cash: '现金', sales: '销售收入', finance: '财务表' }[source] ?? source);
const profileLabel = (code?: string | null) => profiles.find((item) => item.code === code)?.label ?? code ?? '—';
const fileStoreName = (file: ImportFile) => file.store_id ? activeStores.value.find((store) => store.id === file.store_id)?.name ?? `门店 #${file.store_id}` : '工作簿内多门店';
const batchStatusLabel = (status: string) => ({ draft: '草稿', attention_required: '待处理', ready_to_close: '可关账', closed: '已关账' }[status] ?? status);
const batchStatusClass = (status: string) => status === 'closed' ? 'bg-slate-200 text-slate-700' : status === 'ready_to_close' ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700';
const queueStatusLabel = (status: QueueStatus) => ({ ready: '待处理', preflighting: '预检中', importing: '导入中', imported: '已导入', duplicate: '内容重复', attention: '需确认门店', failed: '失败' }[status]);
const queueStatusClass = (status: QueueStatus) => status === 'failed' ? 'bg-rose-50 text-rose-700' : status === 'imported' ? 'bg-emerald-50 text-emerald-700' : status === 'attention' ? 'bg-amber-50 text-amber-700' : 'bg-slate-100 text-slate-600';
const formatDateTime = (value: string) => new Date(value).toLocaleString('zh-CN', { hour12: false });
const errorDetail = (error: unknown) => (error as { response?: { data?: { detail?: string } }; message?: string }).response?.data?.detail || (error as { message?: string }).message || '操作失败';

watch(globalDate, () => { queue.value = []; message.value = null; void loadExistingBatch(); });
onMounted(async () => { stores.value = await api.getStores(); await loadExistingBatch(); });
</script>
