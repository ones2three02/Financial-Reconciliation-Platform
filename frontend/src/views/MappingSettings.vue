<template>
  <div class="h-[calc(100vh-8rem)] flex flex-col fade-in overflow-hidden">
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8 flex-1 min-h-0 overflow-hidden">
      <!-- Create Mapping Form Card -->
      <Card class="h-fit shadow-sm border border-slate-200/80">
        <CardHeader class="pb-4">
          <CardTitle class="flex items-center gap-2.5 text-base font-bold text-slate-800">
            <Plus class="h-4.5 w-4.5 text-blue-500" />
            <span>新增字段映射</span>
          </CardTitle>
          <CardDescription>配置新的三方平台 Excel 列名头以适配标准字段</CardDescription>
        </CardHeader>
        <CardContent class="space-y-4">
          <!-- Source Selector -->
          <div class="flex flex-col gap-1.5">
            <label class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">数据来源通道</label>
            <Select 
              v-model="newMapping.data_source"
              :options="sourceOptions"
              class="h-9"
            />
          </div>

          <!-- Target Field Selector -->
          <div class="flex flex-col gap-1.5">
            <label class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">目标标准系统字段</label>
            <Select 
              v-model="newMapping.target_field"
              :options="targetFieldOptions"
              class="h-9"
            />
          </div>

          <!-- Source Column Input -->
          <div class="flex flex-col gap-1.5">
            <label for="new-column" class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Excel 原始列头 (必须精确一致)</label>
            <Input 
              id="new-column"
              type="text" 
              v-model="newMapping.source_column" 
              placeholder="例如: 终端门店 / 交易金额(元)"
              class="h-9 text-xs"
            />
          </div>

          <Button 
            @click="saveMapping"
            class="w-full bg-blue-600 hover:bg-blue-700 text-white rounded-lg py-2 mt-4 text-xs font-semibold shadow-md shadow-blue-500/10 flex items-center justify-center gap-1.5 h-9"
          >
            <Plus class="w-3.5 h-3.5" />
            <span>保存映射配置</span>
          </Button>
        </CardContent>
      </Card>

      <!-- Mappings List Card -->
      <Card class="lg:col-span-2 shadow-sm border border-slate-200/80 flex flex-col overflow-hidden min-h-0 bg-white">
        <CardHeader class="flex flex-row items-center justify-between flex-wrap gap-4 pb-4">
          <div>
            <CardTitle class="flex items-center gap-2.5 text-base font-bold text-slate-800">
              <Sliders class="h-4.5 w-4.5 text-blue-500" />
              <span>已配置映射规则</span>
            </CardTitle>
            <CardDescription>系统支持的所有来源 Excel 的列头转换匹配规则</CardDescription>
          </div>
          
          <Select 
            v-model="selectedFilterSource" 
            :options="filterSourceOptions"
            @change="fetchMappings"
            class="w-36 h-9"
            align="right"
          />
        </CardHeader>
        <CardContent class="p-4 flex-1 flex flex-col overflow-hidden min-h-0">
          <!-- Mappings Table -->
          <div class="flex-1 overflow-auto min-h-0 rounded-xl border border-slate-200/80">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="sticky top-0 z-10 bg-slate-50 text-slate-400 text-[10px] font-bold uppercase tracking-wider border-b border-slate-200/80 select-none">
                  <th class="sticky top-0 z-10 bg-slate-50 p-4">数据分类</th>
                  <th class="sticky top-0 z-10 bg-slate-50 p-4">目标标准字段</th>
                  <th class="sticky top-0 z-10 bg-slate-50 p-4">Excel 原始列标题</th>
                  <th class="sticky top-0 z-10 bg-slate-50 p-4 text-center">使用状态</th>
                  <th class="sticky top-0 z-10 bg-slate-50 p-4 text-center">操作</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs">
                <tr v-if="filteredMappings.length === 0">
                  <td colspan="5" class="p-8 text-center text-slate-400 font-medium">
                    <div class="flex flex-col items-center justify-center gap-2">
                      <FolderOpen class="w-8 h-8 text-slate-300" />
                      <span>暂无对应的数据源列映射规则</span>
                    </div>
                  </td>
                </tr>
                <tr v-for="m in filteredMappings" :key="m.id" class="hover:bg-slate-50/40 transition-colors">
                  <td class="p-4">
                    <span class="px-2.5 py-1 rounded-full text-[10px] font-semibold select-none" :class="getSourceBadgeClass(m.data_source)">
                      {{ getSourceLabel(m.data_source) }}
                    </span>
                  </td>
                  <td class="p-4">
                    <code class="px-1.5 py-0.5 bg-slate-100 border border-slate-200 rounded text-[10px] font-bold font-mono text-slate-700">
                      {{ m.target_field }}
                    </code>
                  </td>
                  <td class="p-4 font-bold text-slate-800">{{ m.source_column }}</td>
                  <td class="p-4 text-center">
                    <Button 
                      @click="openStatusModal(m)"
                      variant="ghost"
                      size="xs"
                      class="px-2.5 py-1 rounded-full text-[10px] font-bold select-none"
                      :class="m.is_active ? 'bg-emerald-50 text-emerald-600 hover:bg-emerald-100' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'"
                    >
                      <span class="w-1.5 h-1.5 rounded-full mr-1" :class="m.is_active ? 'bg-emerald-500' : 'bg-slate-400'"></span>
                      <span>{{ m.is_active ? '已启用' : '已禁用' }}</span>
                    </Button>
                  </td>
                  <td class="p-4 text-center select-none">
                    <Button
                      @click="openStatusModal(m)"
                      variant="ghost"
                      size="xs"
                      :class="m.is_active ? 'text-amber-600 hover:text-amber-800 hover:bg-amber-50 font-bold' : 'text-emerald-600 hover:text-emerald-800 hover:bg-emerald-50 font-bold'"
                    >
                      {{ m.is_active ? '停用' : '重新启用' }}
                    </Button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>

    <Teleport to="body">
      <div v-if="statusMapping" class="fixed inset-0 z-50 flex items-center justify-center bg-zinc-950/40 p-4 backdrop-blur-sm" @click.self="closeStatusModal">
        <Card class="w-full max-w-md bg-white shadow-2xl">
          <CardHeader><CardTitle class="text-base">{{ statusMapping.is_active ? '停用字段映射' : '重新启用字段映射' }}</CardTitle><CardDescription>{{ getSourceLabel(statusMapping.data_source) }} 的“{{ statusMapping.source_column }}”将{{ statusMapping.is_active ? '不再用于后续文件解析' : '重新用于后续文件解析' }}，历史导入数据不会被删除。</CardDescription></CardHeader>
          <CardContent class="space-y-3">
            <div class="rounded-xl bg-slate-50 p-3 text-xs text-slate-600">目标字段：{{ statusMapping.target_field }}</div>
            <textarea v-model="statusReason" rows="4" maxlength="500" class="w-full rounded-xl border border-slate-200 p-3 text-sm outline-none focus:ring-2 focus:ring-amber-500" :placeholder="statusMapping.is_active ? '请输入停用原因' : '请输入重新启用原因'"></textarea>
          </CardContent>
          <CardFooter class="justify-end gap-3"><Button variant="outline" @click="closeStatusModal">取消</Button><Button :class="statusMapping.is_active ? 'bg-amber-600 text-white hover:bg-amber-700' : 'bg-emerald-600 text-white hover:bg-emerald-700'" :disabled="!statusReason.trim()" @click="submitStatusChange">{{ statusMapping.is_active ? '确认停用' : '确认重新启用' }}</Button></CardFooter>
        </Card>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { api } from '../services/api';
import type { FieldMapping } from '../services/api';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Select } from '../components/ui/select';
import { Sliders, Plus, FolderOpen } from 'lucide-vue-next';

const sources = [
  { value: 'tonglian', label: '通联后台', badge: 'bg-violet-50 text-violet-600' },
  { value: 'meituan', label: '美团收入', badge: 'bg-amber-50 text-amber-600' },
  { value: 'douyin', label: '抖音收入', badge: 'bg-slate-100 text-slate-700' },
  { value: 'cash', label: '现金收入', badge: 'bg-teal-50 text-teal-600' },
  { value: 'sales', label: '销售收入', badge: 'bg-blue-50 text-blue-600' },
];

const sourceOptions = [
  { value: 'tonglian', label: '通联后台' },
  { value: 'meituan', label: '美团收入' },
  { value: 'douyin', label: '抖音收入' },
  { value: 'cash', label: '现金收入' },
  { value: 'sales', label: '销售收入' }
];

const filterSourceOptions = [
  { value: '', label: '全部来源' },
  ...sourceOptions
];

const targetFieldOptions = [
  { value: 'trade_date', label: '交易日期 (trade_date)' },
  { value: 'store_name', label: '门店名称 (store_name)' },
  { value: 'amount', label: '交易金额 (amount)' }
];

const selectedFilterSource = ref('');
const mappings = ref<FieldMapping[]>([]);
const statusMapping = ref<FieldMapping | null>(null);
const statusReason = ref('');

const newMapping = ref({
  data_source: 'tonglian',
  target_field: 'trade_date',
  source_column: '',
});

const getSourceLabel = (val: string) => {
  return sources.find(s => s.value === val)?.label || val;
};

const getSourceBadgeClass = (val: string) => {
  return sources.find(s => s.value === val)?.badge || 'bg-slate-100 text-slate-600';
};

const filteredMappings = computed(() => {
  if (!selectedFilterSource.value) return mappings.value;
  return mappings.value.filter(m => m.data_source === selectedFilterSource.value);
});

const fetchMappings = async () => {
  try {
    mappings.value = await api.getFieldMappings();
  } catch (error) {
    console.error('Failed to load field mappings:', error);
  }
};

const saveMapping = async () => {
  if (!newMapping.value.source_column.trim()) {
    alert('请输入Excel中的列名标题！');
    return;
  }
  
  try {
    await api.createFieldMapping({
      data_source: newMapping.value.data_source,
      target_field: newMapping.value.target_field,
      source_column: newMapping.value.source_column.trim(),
    });
    newMapping.value.source_column = '';
    fetchMappings();
  } catch (error) {
    alert('保存字段映射失败！');
  }
};

const openStatusModal = (mapping: FieldMapping) => {
  statusMapping.value = mapping;
  statusReason.value = '';
};

const closeStatusModal = () => {
  statusMapping.value = null;
  statusReason.value = '';
};

const submitStatusChange = async () => {
  if (!statusMapping.value || !statusReason.value.trim()) return;
  try {
    await api.updateFieldMapping(statusMapping.value.id, {
      is_active: !statusMapping.value.is_active,
      status_change_reason: statusReason.value.trim(),
    });
    closeStatusModal();
    await fetchMappings();
  } catch (error: any) {
    alert(error.response?.data?.detail || '修改状态失败！');
  }
};

onMounted(() => {
  fetchMappings();
});
</script>
