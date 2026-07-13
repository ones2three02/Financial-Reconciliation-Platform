<template>
  <div class="space-y-8 fade-in">
    <!-- File Upload Section -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <!-- Upload Config Card -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 flex flex-col justify-between">
        <div class="space-y-5">
          <div>
            <h3 class="text-lg font-bold text-slate-800">1. 选择数据来源</h3>
            <p class="text-xs text-slate-400">请准确分类上传的文件，这将直接影响字段映射和清洗逻辑</p>
          </div>
          
          <div class="space-y-3">
            <label 
              v-for="source in sources" 
              :key="source.value"
              class="flex items-center justify-between p-4 rounded-xl border border-slate-200 cursor-pointer transition-all duration-150 hover:bg-slate-50/50"
              :class="{'border-blue-500 bg-blue-50/20 ring-1 ring-blue-500': selectedSource === source.value}"
            >
              <div class="flex items-center gap-3">
                <input 
                  type="radio" 
                  name="source" 
                  :value="source.value" 
                  v-model="selectedSource"
                  class="text-blue-600 focus:ring-blue-500"
                />
                <span class="font-semibold text-sm text-slate-800">{{ source.label }}</span>
              </div>
              <span class="text-xs text-slate-400">{{ source.desc }}</span>
            </label>
          </div>
        </div>
      </div>

      <!-- Drag & Drop Upload Zone -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 lg:col-span-2 flex flex-col justify-between min-h-[300px]">
        <div>
          <h3 class="text-lg font-bold text-slate-800">2. 拖入或选择 Excel 文件</h3>
          <p class="text-xs text-slate-400">支持批量上传，系统会自动完成行列解析、清洗和门店配对</p>
        </div>

        <div 
          @dragover.prevent="dragOver = true"
          @dragleave.prevent="dragOver = false"
          @drop.prevent="handleDrop"
          @click="triggerFileSelect"
          class="flex-1 border-2 border-dashed rounded-2xl my-5 flex flex-col items-center justify-center cursor-pointer transition-all duration-200 group text-slate-400 hover:text-slate-600"
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
          <span class="text-4xl mb-3 group-hover:scale-110 transition-transform">📂</span>
          <span class="font-bold text-sm text-slate-700">点击选择或拖入 Excel 文件到这里</span>
          <span class="text-xs text-slate-400 mt-1">支持扩展名: .xlsx, .xls</span>
        </div>

        <div v-if="uploadQueue.length > 0" class="space-y-2">
          <div class="text-xs font-semibold text-slate-500 mb-1">正在上传 ({{ uploadQueue.length }}) :</div>
          <div 
            v-for="item in uploadQueue" 
            :key="item.name"
            class="flex items-center justify-between text-xs p-3 bg-slate-50 rounded-xl border border-slate-100"
          >
            <div class="flex items-center gap-2 max-w-[70%] truncate">
              <span>📄</span>
              <span class="font-semibold text-slate-700 truncate">{{ item.name }}</span>
            </div>
            <div class="flex items-center gap-3">
              <span v-if="item.status === 'uploading'" class="text-blue-500 font-medium animate-pulse">正在上传...</span>
              <span v-else-if="item.status === 'success'" class="text-emerald-500 font-medium">✓ 处理完成</span>
              <span v-else class="text-rose-500 font-medium">✗ {{ item.error }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Import History Table -->
    <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 space-y-6">
      <div class="flex items-center justify-between">
        <div>
          <h3 class="text-lg font-bold text-slate-800">导入日志</h3>
          <p class="text-xs text-slate-500">查看历史 Excel 导入记录及其数据清洗/对账状态</p>
        </div>
        <button 
          @click="fetchImportHistory" 
          class="px-4 py-2 border border-slate-200 rounded-xl text-xs font-medium hover:bg-slate-50 transition-colors"
        >
          🔄 刷新日志
        </button>
      </div>

      <div class="overflow-x-auto rounded-xl border border-slate-100">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-slate-50 text-slate-400 text-xs font-semibold uppercase tracking-wider border-b border-slate-100">
              <th class="p-4">文件名称</th>
              <th class="p-4">数据分类</th>
              <th class="p-4">上传时间</th>
              <th class="p-4 text-center">状态</th>
              <th class="p-4 text-center">解析行数</th>
              <th class="p-4">异常日志</th>
              <th class="p-4 text-center">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 text-sm">
            <tr v-if="history.length === 0">
              <td colspan="7" class="p-8 text-center text-slate-400 text-sm">暂无上传记录</td>
            </tr>
            <tr v-for="item in history" :key="item.id" class="hover:bg-slate-50/50 transition-colors">
              <td class="p-4 font-semibold text-slate-700">{{ item.filename }}</td>
              <td class="p-4">
                <span class="px-2.5 py-1 rounded-full text-xs font-medium" :class="getSourceBadgeClass(item.data_source)">
                  {{ getSourceLabel(item.data_source) }}
                </span>
              </td>
              <td class="p-4 text-slate-500">{{ formatDate(item.uploaded_at) }}</td>
              <td class="p-4 text-center">
                <span 
                  class="px-2.5 py-1 rounded-full text-xs font-semibold"
                  :class="{
                    'bg-emerald-50 text-emerald-600': item.upload_status === 'parsed',
                    'bg-blue-50 text-blue-600': item.upload_status === 'pending',
                    'bg-rose-50 text-rose-600': item.upload_status === 'failed',
                  }"
                >
                  {{ getStatusLabel(item.upload_status) }}
                </span>
              </td>
              <td class="p-4 text-center font-medium text-slate-600">{{ item.row_count }}</td>
              <td class="p-4 text-slate-400 max-w-xs truncate" :title="item.error_message || ''">
                {{ item.error_message || '—' }}
              </td>
              <td class="p-4 text-center">
                <button 
                  @click="reprocessFile(item.id)" 
                  class="text-xs font-semibold text-blue-600 hover:text-blue-800 transition-colors disabled:opacity-50"
                  :disabled="reprocessingId === item.id"
                >
                  {{ reprocessingId === item.id ? '重新计算中...' : '🔄 重新清洗' }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { api } from '../services/api';
import type { ImportFile } from '../services/api';

const sources = [
  { value: 'tonglian', label: '通联后台', desc: '第三方好老板系统流水', badge: 'bg-violet-50 text-violet-600' },
  { value: 'meituan', label: '美团收入', desc: '美团团购核销对账数据', badge: 'bg-amber-50 text-amber-600' },
  { value: 'douyin', label: '抖音收入', desc: '抖音本地生活核销流水', badge: 'bg-slate-100 text-slate-700' },
  { value: 'cash', label: '现金收入', desc: '门店手工交班现金账', badge: 'bg-teal-50 text-teal-600' },
  { value: 'sales', label: '销售收入', desc: '收银系统 ERP/POS 销售汇总', badge: 'bg-blue-50 text-blue-600' },
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
    case 'parsed': return '✓ 已清洗';
    case 'pending': return '⏳ 正在处理';
    case 'failed': return '✗ 失败';
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
  
  // Refresh history after all uploads complete
  fetchImportHistory();
  
  // Clear success items after 5 seconds
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
