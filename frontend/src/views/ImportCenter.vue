<template>
  <div class="space-y-8 fade-in">
    <!-- File Upload Section -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <!-- Upload Config Card -->
      <Card class="shadow-sm border border-slate-200/80 flex flex-col justify-between">
        <CardHeader class="pb-4">
          <CardTitle class="flex items-center gap-2.5 text-base font-bold text-slate-800">
            <Sliders class="h-4.5 w-4.5 text-blue-500" />
            <span>1. 选择数据来源</span>
          </CardTitle>
          <CardDescription>选择您将要导入的 Excel 文件的账目渠道归属</CardDescription>
        </CardHeader>
        <CardContent class="space-y-3">
          <label 
            v-for="source in sources" 
            :key="source.value"
            class="flex items-center justify-between p-3.5 rounded-xl border border-slate-200 cursor-pointer transition-all duration-150 hover:bg-slate-50/50"
            :class="{'border-blue-500 bg-blue-50/15 ring-1 ring-blue-500/20': selectedSource === source.value}"
          >
            <div class="flex items-center gap-3">
              <input 
                type="radio" 
                name="source" 
                :value="source.value" 
                v-model="selectedSource"
                class="text-blue-600 focus:ring-blue-500 h-4 w-4"
              />
              <span class="font-bold text-xs text-slate-800">{{ source.label }}</span>
            </div>
            <span class="text-[10px] font-semibold text-slate-400">{{ source.desc }}</span>
          </label>

          <!-- Explicit store selection for cash/sales sources -->
          <div v-if="selectedSource === 'cash' || selectedSource === 'sales'" class="mt-4 pt-4 border-t border-slate-100 flex flex-col gap-1.5">
            <label class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">指定报表归属标准门店</label>
            <Select 
              v-model="selectedStoreId"
              :options="stores.map(s => ({ value: s.id, label: s.name }))"
              placeholder="-- 请选择该报表归属的标准门店 --"
              class="h-9"
            />
          </div>
        </CardContent>
      </Card>

      <!-- Drag & Drop Upload Zone -->
      <Card class="lg:col-span-2 shadow-sm border border-slate-200/80 flex flex-col justify-between min-h-[300px]">
        <CardHeader class="pb-2">
          <CardTitle class="flex items-center gap-2.5 text-base font-bold text-slate-800">
            <UploadCloud class="h-4.5 w-4.5 text-blue-500" />
            <span>2. 拖入或选择 Excel 文件</span>
          </CardTitle>
          <CardDescription>支持批量拖拽多张 Excel 表，系统会自动提取记录并自动重对账</CardDescription>
        </CardHeader>
        <CardContent class="flex-1 flex flex-col justify-between mt-2">
          <div 
            @dragover.prevent="dragOver = true"
            @dragleave.prevent="dragOver = false"
            @drop.prevent="handleDrop"
            @click="triggerFileSelect"
            class="flex-1 border-2 border-dashed rounded-xl py-8 flex flex-col items-center justify-center cursor-pointer transition-all duration-200 group text-slate-400 hover:text-slate-600 min-h-[160px]"
            :class="dragOver ? 'border-blue-500 bg-blue-50/10' : 'border-slate-200 hover:border-slate-300 bg-slate-50/50'"
          >
            <input 
              type="file" 
              ref="fileInputRef" 
              multiple 
              accept=".xlsx, .xls"
              class="hidden" 
              @change="handleFileSelect"
            />
            <UploadCloud class="w-10 h-10 text-slate-300 group-hover:scale-105 transition-transform mb-2.5 group-hover:text-blue-500" />
            <span class="font-bold text-xs text-slate-700">点击选择或拖入 Excel 文件到这里</span>
            <span class="text-[10px] text-slate-400 mt-1">仅限扩展名: .xlsx, .xls</span>
          </div>

          <!-- Queue progress -->
          <div v-if="uploadQueue.length > 0" class="mt-4 space-y-2">
            <div class="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">本次导入任务 ({{ uploadQueue.length }})</div>
            <div 
              v-for="item in uploadQueue" 
              :key="item.name"
              class="flex items-center justify-between text-xs p-3 bg-slate-50 border border-slate-200/60 rounded-xl"
            >
              <div class="flex items-center gap-2 max-w-[70%] truncate">
                <FileSpreadsheet class="w-4 h-4 text-emerald-600 shrink-0" />
                <span class="font-bold text-slate-700 truncate">{{ item.name }}</span>
              </div>
              <div class="flex items-center gap-3 shrink-0">
                <span v-if="item.status === 'uploading'" class="text-blue-500 font-bold animate-pulse text-[11px]">⏳ 处理中...</span>
                <span v-else-if="item.status === 'success'" class="text-emerald-500 font-bold text-[11px] inline-flex items-center gap-1">
                  <CheckCircle2 class="w-3.5 h-3.5" /> 已导入
                </span>
                <span v-else class="text-rose-500 font-bold text-[11px]" :title="item.error">✗ {{ item.error && item.error.length > 15 ? item.error.substring(0, 15) + '...' : item.error }}</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- Import History Table -->
    <Card class="shadow-sm border border-slate-200/80">
      <CardHeader class="flex flex-row items-center justify-between flex-wrap gap-4 pb-4">
        <div>
          <CardTitle class="flex items-center gap-2.5 text-base font-bold text-slate-800">
            <History class="h-4.5 w-4.5 text-blue-500" />
            <span>导入历史日志</span>
          </CardTitle>
          <CardDescription>追溯已上传文件的清洗历史、解析行数与对账状态日志</CardDescription>
        </div>
        <!-- Search and refresh controls -->
        <div class="flex items-center gap-3">
          <Input 
            v-model="searchQuery" 
            placeholder="搜索文件名..." 
            class="h-8.5 w-48 text-xs font-semibold rounded-lg"
          />
          <Button 
            @click="fetchImportHistory" 
            variant="outline"
            size="sm"
            class="h-8.5 text-xs font-semibold border border-slate-200/80 hover:bg-slate-50 flex items-center gap-1"
          >
            🔄 刷新日志
          </Button>
        </div>
      </CardHeader>
      <CardContent class="p-0">
        <div class="overflow-hidden border-t border-slate-100">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-50 text-slate-400 text-[10px] font-bold uppercase tracking-wider border-b border-slate-200/80">
                <th class="p-4">文件名称</th>
                <th class="p-4">数据分类</th>
                <th class="p-4">归属门店</th>
                <th class="p-4">上传时间</th>
                <th class="p-4 text-center">状态</th>
                <th class="p-4 text-center">解析记录数</th>
                <th class="p-4">异常日志</th>
                <th class="p-4 text-center">操作</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-xs">
              <tr v-if="paginatedHistory.length === 0">
                <td colspan="8" class="p-8 text-center text-slate-400 font-medium">
                  <div class="flex flex-col items-center justify-center gap-2">
                    <FolderOpen class="w-8 h-8 text-slate-300" />
                    <span>暂无满足条件的上传记录</span>
                  </div>
                </td>
              </tr>
              <tr v-for="item in paginatedHistory" :key="item.id" class="hover:bg-slate-50/40 transition-colors">
                <td class="p-4 font-bold text-slate-700 flex items-center gap-2">
                  <FileSpreadsheet class="w-4 h-4 text-emerald-600 shrink-0" />
                  <span class="truncate max-w-[200px]" :title="item.filename">{{ item.filename }}</span>
                </td>
                <td class="p-4">
                  <span class="px-2.5 py-1 rounded-full text-[10px] font-semibold" :class="getSourceBadgeClass(item.data_source)">
                    {{ getSourceLabel(item.data_source) }}
                  </span>
                </td>
                <td class="p-4">
                  <span v-if="item.store_id" class="font-bold text-slate-700">
                    {{ getStoreNameById(item.store_id) }}
                  </span>
                  <span v-else class="text-slate-400 font-medium">多店表自动拆分</span>
                </td>
                <td class="p-4 text-slate-500 font-mono">{{ formatDate(item.uploaded_at) }}</td>
                <td class="p-4 text-center">
                  <span 
                    class="px-2.5 py-0.5 rounded-full text-[10px] font-bold"
                    :class="{
                      'bg-emerald-50 text-emerald-600 border border-emerald-250': item.upload_status === 'parsed',
                      'bg-blue-50 text-blue-600 border border-blue-250': item.upload_status === 'pending_mapping' || item.upload_status === 'pending',
                      'bg-rose-50 text-rose-600 border border-rose-250': item.upload_status === 'failed',
                    }"
                  >
                    {{ getStatusLabel(item.upload_status) }}
                  </span>
                </td>
                <td class="p-4 text-center font-bold text-slate-600">{{ item.row_count }} 行</td>
                <td class="p-4 text-slate-400 max-w-xs truncate" :title="item.error_message || ''">
                  {{ item.error_message || '—' }}
                </td>
                <td class="p-4 text-center">
                  <div class="flex items-center justify-center gap-2">
                    <template v-if="deletingId === item.id">
                      <span class="text-rose-500 font-bold text-[11px] mr-1">确定删除该数据？</span>
                      <Button 
                        @click="deleteFile(item.id)" 
                        variant="ghost"
                        size="xs"
                        class="text-xs font-bold text-rose-600 hover:text-rose-800 bg-rose-50 px-1.5 py-0.5 rounded"
                      >
                        确定
                      </Button>
                      <Button 
                        @click="deletingId = null" 
                        variant="ghost"
                        size="xs"
                        class="text-xs font-bold text-slate-500 hover:text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded"
                      >
                        取消
                      </Button>
                    </template>
                    <template v-else>
                      <Button 
                        @click="reprocessFile(item.id)" 
                        variant="ghost"
                        size="xs"
                        class="text-xs font-bold text-blue-600 hover:text-blue-800"
                        :disabled="reprocessingId === item.id || deletingId !== null"
                      >
                        {{ reprocessingId === item.id ? '重算中...' : '🔄 重新对账' }}
                      </Button>
                      <Button 
                        @click="deletingId = item.id" 
                        variant="ghost"
                        size="xs"
                        class="text-xs font-bold text-rose-600 hover:text-rose-800"
                        :disabled="reprocessingId !== null || deletingId !== null"
                      >
                        🗑 删除
                      </Button>
                    </template>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Pagination Controls -->
        <div v-if="totalPages > 1" class="flex items-center justify-between px-4 py-3 border-t border-slate-200 bg-slate-50/50 text-xs">
          <div class="text-slate-400 font-medium select-none">
            显示第 {{ (currentPage - 1) * pageSize + 1 }} 至 {{ Math.min(currentPage * pageSize, filteredHistory.length) }} 条记录，共 {{ filteredHistory.length }} 条
          </div>
          <div class="flex items-center gap-2">
            <Button 
              size="xs" 
              variant="outline" 
              :disabled="currentPage === 1" 
              @click="currentPage--"
              class="h-7 text-[11px] font-bold border-slate-200/80 hover:bg-slate-50"
            >
              上一页
            </Button>
            <span class="text-slate-600 font-bold px-2 select-none">第 {{ currentPage }} / {{ totalPages }} 页</span>
            <Button 
              size="xs" 
              variant="outline" 
              :disabled="currentPage === totalPages" 
              @click="currentPage++"
              class="h-7 text-[11px] font-bold border-slate-200/80 hover:bg-slate-50"
            >
              下一页
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>

    <!-- Column Mapping Confirmation Modal Dialog -->
    <div 
      v-if="showMappingModal" 
      class="fixed inset-0 bg-zinc-950/40 backdrop-blur-sm z-50 flex items-center justify-center p-4 fade-in"
      @click.self="showMappingModal = false"
    >
      <Card class="w-full max-w-md shadow-2xl border border-slate-200/80 overflow-hidden bg-white">
        <CardHeader class="bg-slate-50/50 border-b border-slate-200/60 pb-4">
          <div class="flex items-center justify-between">
            <div>
              <CardTitle class="text-base font-bold text-slate-800">手动指定表头列映射</CardTitle>
              <CardDescription class="text-xs text-slate-400 mt-1">
                未能自动匹配文件 [{{ mappingContext.filename }}] 的核心列，请核对指派：
              </CardDescription>
            </div>
            <button @click="showMappingModal = false" class="text-slate-400 hover:text-slate-600 text-lg font-bold">×</button>
          </div>
        </CardHeader>
        
        <CardContent class="p-6 space-y-4">
          <!-- Trade Date Mapping -->
          <div class="flex flex-col gap-1.5">
            <label class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">账期日期列</label>
            <Select 
              v-model="chosenMappings.trade_date"
              :options="mappingContext.columns.map(c => ({ value: c, label: c }))"
              placeholder="-- 选择 Excel 中代表账期日期的列 --"
              class="h-9"
            />
          </div>

          <!-- Store Name Mapping -->
          <div class="flex flex-col gap-1.5">
            <label class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">门店名称列</label>
            <Select 
              v-model="chosenMappings.store_name"
              :options="mappingContext.columns.map(c => ({ value: c, label: c }))"
              placeholder="-- 选择 Excel 中代表门店名称的列 --"
              class="h-9"
            />
          </div>

          <!-- Amount Mapping -->
          <div class="flex flex-col gap-1.5">
            <label class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">交易金额列</label>
            <Select 
              v-model="chosenMappings.amount"
              :options="mappingContext.columns.map(c => ({ value: c, label: c }))"
              placeholder="-- 选择 Excel 中代表交易金额的列 --"
              class="h-9"
            />
          </div>
        </CardContent>

        <CardFooter class="bg-slate-50/50 border-t border-slate-200/60 p-4 flex justify-end gap-3">
          <Button 
            @click="showMappingModal = false"
            variant="outline"
            size="sm"
            class="h-8 text-xs font-semibold"
          >
            取消
          </Button>
          <Button 
            @click="submitColumnMapping"
            :disabled="isSubmittingMapping"
            size="sm"
            class="h-8 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs shadow-md shadow-blue-500/10 flex items-center gap-1.5"
          >
            <Save class="w-3.5 h-3.5" />
            <span>{{ isSubmittingMapping ? '正在处理...' : '确认导入' }}</span>
          </Button>
        </CardFooter>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue';
import { api } from '../services/api';
import type { ImportFile } from '../services/api';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Select } from '../components/ui/select';
import { Sliders, UploadCloud, FileSpreadsheet, CheckCircle2, History, FolderOpen, Save } from 'lucide-vue-next';

const sources = [
  { value: 'tonglian', label: '通联后台', desc: '第三方好老板系统流水', badge: 'bg-violet-50 text-violet-600 border border-violet-100' },
  { value: 'meituan', label: '美团收入', desc: '美团团购核销对账数据', badge: 'bg-amber-50 text-amber-600 border border-amber-100' },
  { value: 'douyin', label: '抖音收入', desc: '抖音本地生活核销流水', badge: 'bg-slate-100 text-slate-700 border border-slate-200' },
  { value: 'cash', label: '现金收入', desc: '门店手工交班现金账', badge: 'bg-teal-50 text-teal-600 border border-teal-100' },
  { value: 'sales', label: '销售收入', desc: '收银系统 ERP/POS 销售汇总', badge: 'bg-blue-50 text-blue-600 border border-blue-100' },
];

const selectedSource = ref('tonglian');
const dragOver = ref(false);
const fileInputRef = ref<HTMLInputElement | null>(null);
const history = ref<ImportFile[]>([]);
const reprocessingId = ref<number | null>(null);

// Pagination and Search states
const searchQuery = ref('');
const currentPage = ref(1);
const pageSize = ref(10);

// Store states
const selectedStoreId = ref<number | null>(null);
const stores = ref<any[]>([]);
const deletingId = ref<number | null>(null);

// Column mapping modal states
const showMappingModal = ref(false);
const isSubmittingMapping = ref(false);
const mappingContext = ref({
  import_file_id: 0,
  filename: '',
  data_source: '',
  columns: [] as string[],
  detected_mappings: {} as Record<string, string>
});
const chosenMappings = ref({
  trade_date: '',
  store_name: '',
  amount: ''
});

interface UploadItem {
  name: string;
  status: 'uploading' | 'success' | 'failed';
  error?: string;
}
const uploadQueue = ref<UploadItem[]>([]);

const getSourceLabel = (val: string) => {
  return sources.find(s => s.value === val)?.label || val;
};

const getSourceBadgeClass = (val: string) => {
  return sources.find(s => s.value === val)?.badge || 'bg-slate-100 text-slate-600';
};

const getStatusLabel = (val: string) => {
  switch (val) {
    case 'parsed': return '已完成';
    case 'pending': return '待处理';
    case 'pending_mapping': return '待指派表头';
    case 'failed': return '处理失败';
    default: return val;
  }
};

const getStoreNameById = (id: number) => {
  return stores.value.find(s => s.id === id)?.name || `ID: ${id}`;
};

const formatDate = (dateStr: string) => {
  const d = new Date(dateStr);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
};

// Filtered and Paginated computed history
const filteredHistory = computed(() => {
  if (!searchQuery.value.trim()) return history.value;
  const q = searchQuery.value.toLowerCase().trim();
  return history.value.filter(item => item.filename.toLowerCase().includes(q));
});

const totalPages = computed(() => Math.ceil(filteredHistory.value.length / pageSize.value) || 1);

const paginatedHistory = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  const end = start + pageSize.value;
  return filteredHistory.value.slice(start, end);
});

// Reset page on search
watch(searchQuery, () => {
  currentPage.value = 1;
});

// Reset selected store when data source changes
watch(selectedSource, () => {
  selectedStoreId.value = null;
});

const fetchImportHistory = async () => {
  try {
    history.value = await api.getImportFiles();
  } catch (error) {
    console.error('Failed to load history:', error);
  }
};

const fetchStores = async () => {
  try {
    stores.value = await api.getStores();
  } catch (error) {
    console.error('Failed to load stores:', error);
  }
};

const triggerFileSelect = () => {
  fileInputRef.value?.click();
};

const handleFileSelect = (e: Event) => {
  const files = (e.target as HTMLInputElement).files;
  if (files) {
    uploadFiles(Array.from(files));
  }
};

const handleDrop = (e: DragEvent) => {
  dragOver.value = false;
  const files = e.dataTransfer?.files;
  if (files) {
    uploadFiles(Array.from(files));
  }
};

const uploadFiles = async (files: File[]) => {
  for (const file of files) {
    const queueItem: UploadItem = {
      name: file.name,
      status: 'uploading'
    };
    uploadQueue.value.unshift(queueItem);
    
    // Explicit selection check for Cash/Sales
    if ((selectedSource.value === 'cash' || selectedSource.value === 'sales') && !selectedStoreId.value) {
      queueItem.status = 'failed';
      queueItem.error = '导入单店账时请先指定归属门店！';
      continue;
    }
    
    try {
      const res = await api.uploadFile(file, selectedSource.value, selectedStoreId.value);
      if (res && res.status === 'requires_column_mapping') {
        queueItem.status = 'failed';
        queueItem.error = '需要手动指定列头';
        
        mappingContext.value = {
          import_file_id: res.import_file_id,
          filename: res.filename,
          data_source: res.data_source,
          columns: res.columns,
          detected_mappings: res.detected_mappings
        };
        
        chosenMappings.value = {
          trade_date: res.detected_mappings.trade_date || '',
          store_name: res.detected_mappings.store_name || '',
          amount: res.detected_mappings.amount || ''
        };
        
        showMappingModal.value = true;
      } else {
        queueItem.status = 'success';
      }
    } catch (err: any) {
      queueItem.status = 'failed';
      queueItem.error = err.response?.data?.detail || '解析失败';
    }
  }
  
  fetchImportHistory();
  
  setTimeout(() => {
    uploadQueue.value = uploadQueue.value.filter(item => item.status === 'failed');
  }, 5000);
};

const submitColumnMapping = async () => {
  if (!chosenMappings.value.trade_date || !chosenMappings.value.store_name || !chosenMappings.value.amount) {
    alert('请为所有 3 个标准字段指定对应的 Excel 列名！');
    return;
  }
  isSubmittingMapping.value = true;
  try {
    await api.confirmMapping(mappingContext.value.import_file_id, chosenMappings.value);
    showMappingModal.value = false;
    alert('映射确认成功，数据已完成对账！');
    fetchImportHistory();
  } catch (err: any) {
    alert('确认映射失败: ' + (err.response?.data?.detail || '未知错误'));
  } finally {
    isSubmittingMapping.value = false;
  }
};

const deleteFile = async (fileId: number) => {
  try {
    await api.deleteImportFile(fileId);
    alert('文件数据及清洗对账结果已成功完全清除！');
    deletingId.value = null;
    fetchImportHistory();
  } catch (err: any) {
    alert('删除文件失败: ' + (err.response?.data?.detail || '未知错误'));
  }
};

const reprocessFile = async (fileId: number) => {
  reprocessingId.value = fileId;
  try {
    await api.reprocessFile(fileId);
    alert('重新处理成功，对账结果已刷新！');
    fetchImportHistory();
  } catch (err: any) {
    alert('重新处理失败: ' + (err.response?.data?.detail || '未知错误'));
  } finally {
    reprocessingId.value = null;
  }
};

onMounted(() => {
  fetchImportHistory();
  fetchStores();
});
</script>
