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
            <div class="mt-1 text-lg font-extrabold text-slate-800">{{ batchDetail?.import_files.length ?? 0 }} 份</div>
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
      <CardHeader>
        <CardTitle class="flex items-center gap-2 text-base"><History class="h-4 w-4 text-blue-600" />当前批次导入记录</CardTitle>
        <CardDescription>原始导入不可物理删除；需要修正时重新导入新版本，历史记录继续用于审计追溯。</CardDescription>
      </CardHeader>
      <CardContent class="p-0">
        <div class="overflow-x-auto border-t border-slate-100">
          <table class="w-full text-left text-xs">
            <thead class="bg-slate-50 text-[10px] uppercase tracking-wider text-slate-400">
              <tr><th class="p-4">文件</th><th class="p-4">模板</th><th class="p-4">来源</th><th class="p-4">行数</th><th class="p-4">状态</th><th class="p-4">导入时间</th></tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <tr v-if="!batchDetail?.import_files.length"><td colspan="6" class="p-8 text-center text-slate-400">该账期尚未导入文件</td></tr>
              <tr v-for="file in batchDetail?.import_files ?? []" :key="file.id">
                <td class="p-4 font-bold text-slate-700">{{ file.filename }}</td>
                <td class="p-4 text-slate-500">{{ profileLabel(file.profile_code) }}</td>
                <td class="p-4 text-slate-500">{{ sourceLabel(file.data_source) }}</td>
                <td class="p-4 text-slate-500">{{ file.row_count }}</td>
                <td class="p-4"><span class="rounded-full bg-slate-100 px-2 py-1 font-bold text-slate-600">{{ file.upload_status }}</span></td>
                <td class="p-4 font-mono text-slate-500">{{ formatDateTime(file.uploaded_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { CalendarRange, FileSpreadsheet, History, Sliders, UploadCloud } from 'lucide-vue-next';
import { api, getSession } from '../services/api';
import type { BatchDetail, PreflightResult, ProfileCode, ReconciliationBatch, Store } from '../services/api';
import { globalDate } from '../services/store';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
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

const activeStores = computed(() => stores.value.filter((store) => store.is_active));
const canOperate = computed(() => ['admin', 'finance'].includes(getSession().role ?? ''));
const openIssueCount = computed(() => batchDetail.value?.quality_issues.filter((issue) => issue.status === 'open').length ?? 0);
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

const sourceLabel = (source: string) => ({ tonglian: '通联', meituan: '美团', douyin: '抖音', cash: '现金', sales: '销售收入', finance: '财务表' }[source] ?? source);
const profileLabel = (code?: string | null) => profiles.find((item) => item.code === code)?.label ?? code ?? '—';
const batchStatusLabel = (status: string) => ({ draft: '草稿', attention_required: '待处理', ready_to_close: '可关账', closed: '已关账' }[status] ?? status);
const batchStatusClass = (status: string) => status === 'closed' ? 'bg-slate-200 text-slate-700' : status === 'ready_to_close' ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700';
const queueStatusLabel = (status: QueueStatus) => ({ ready: '待处理', preflighting: '预检中', importing: '导入中', imported: '已导入', duplicate: '内容重复', attention: '需确认门店', failed: '失败' }[status]);
const queueStatusClass = (status: QueueStatus) => status === 'failed' ? 'bg-rose-50 text-rose-700' : status === 'imported' ? 'bg-emerald-50 text-emerald-700' : status === 'attention' ? 'bg-amber-50 text-amber-700' : 'bg-slate-100 text-slate-600';
const formatDateTime = (value: string) => new Date(value).toLocaleString('zh-CN', { hour12: false });
const errorDetail = (error: unknown) => (error as { response?: { data?: { detail?: string } }; message?: string }).response?.data?.detail || (error as { message?: string }).message || '操作失败';

watch(globalDate, () => { queue.value = []; message.value = null; void loadExistingBatch(); });
onMounted(async () => { stores.value = await api.getStores(); await loadExistingBatch(); });
</script>
