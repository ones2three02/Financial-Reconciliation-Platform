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
                <span v-else class="text-rose-500 font-bold text-[11px]">✗ {{ item.error }}</span>
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
        <Button 
          @click="fetchImportHistory" 
          variant="outline"
          size="sm"
          class="h-8 text-xs font-semibold"
        >
          🔄 刷新日志
        </Button>
      </CardHeader>
      <CardContent>
        <div class="overflow-hidden rounded-xl border border-slate-200/80">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-50 text-slate-400 text-[10px] font-bold uppercase tracking-wider border-b border-slate-200/80">
                <th class="p-4">文件名称</th>
                <th class="p-4">数据分类</th>
                <th class="p-4">上传时间</th>
                <th class="p-4 text-center">状态</th>
                <th class="p-4 text-center">解析记录数</th>
                <th class="p-4">异常日志</th>
                <th class="p-4 text-center">操作</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-xs">
              <tr v-if="history.length === 0">
                <td colspan="7" class="p-8 text-center text-slate-400 font-medium">
                  <div class="flex flex-col items-center justify-center gap-2">
                    <FolderOpen class="w-8 h-8 text-slate-300" />
                    <span>暂无上传记录</span>
                  </div>
                </td>
              </tr>
              <tr v-for="item in history" :key="item.id" class="hover:bg-slate-50/40 transition-colors">
                <td class="p-4 font-bold text-slate-700 flex items-center gap-2">
                  <FileSpreadsheet class="w-4 h-4 text-emerald-600" />
                  <span>{{ item.filename }}</span>
                </td>
                <td class="p-4">
                  <span class="px-2.5 py-1 rounded-full text-[10px] font-semibold" :class="getSourceBadgeClass(item.data_source)">
                    {{ getSourceLabel(item.data_source) }}
                  </span>
                </td>
                <td class="p-4 text-slate-500">{{ formatDate(item.uploaded_at) }}</td>
                <td class="p-4 text-center">
                  <span 
                    class="px-2.5 py-0.5 rounded-full text-[10px] font-bold"
                    :class="{
                      'bg-emerald-50 text-emerald-600 border border-emerald-200': item.upload_status === 'parsed',
                      'bg-blue-50 text-blue-600 border border-blue-200': item.upload_status === 'pending',
                      'bg-rose-50 text-rose-600 border border-rose-200': item.upload_status === 'failed',
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
                  <Button 
                    @click="reprocessFile(item.id)" 
                    variant="ghost"
                    size="xs"
                    class="text-xs font-bold text-blue-600 hover:text-blue-800"
                    :disabled="reprocessingId === item.id"
                  >
                    {{ reprocessingId === item.id ? '重算中...' : '🔄 重新对账' }}
                  </Button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { api } from '../services/api';
import type { ImportFile } from '../services/api';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Sliders, UploadCloud, FileSpreadsheet, CheckCircle2, History, FolderOpen } from 'lucide-vue-next';

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
    case 'failed': return '处理失败';
    default: return val;
  }
};

const formatDate = (dateStr: string) => {
  const d = new Date(dateStr);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
};

const fetchImportHistory = async () => {
  try {
    history.value = await api.getImportFiles();
  } catch (error) {
    console.error('Failed to load history:', error);
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
    
    try {
      await api.uploadFile(file, selectedSource.value);
      queueItem.status = 'success';
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
});
</script>
