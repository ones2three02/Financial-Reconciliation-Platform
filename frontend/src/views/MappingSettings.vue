<template>
  <div class="space-y-8 fade-in">
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
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
            <label for="new-source" class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">数据来源通道</label>
            <select 
              id="new-source"
              v-model="newMapping.data_source"
              class="border border-slate-200 rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white font-medium select-custom"
            >
              <option v-for="s in sources" :key="s.value" :value="s.value">{{ s.label }}</option>
            </select>
          </div>

          <!-- Target Field Selector -->
          <div class="flex flex-col gap-1.5">
            <label for="new-target" class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">目标标准系统字段</label>
            <select 
              id="new-target"
              v-model="newMapping.target_field"
              class="border border-slate-200 rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white font-medium select-custom"
            >
              <option value="trade_date">交易日期 (trade_date)</option>
              <option value="store_name">门店名称 (store_name)</option>
              <option value="amount">交易金额 (amount)</option>
            </select>
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
      <Card class="lg:col-span-2 shadow-sm border border-slate-200/80">
        <CardHeader class="flex flex-row items-center justify-between flex-wrap gap-4 pb-4">
          <div>
            <CardTitle class="flex items-center gap-2.5 text-base font-bold text-slate-800">
              <Sliders class="h-4.5 w-4.5 text-blue-500" />
              <span>已配置映射规则</span>
            </CardTitle>
            <CardDescription>系统支持的所有来源 Excel 的列头转换匹配规则</CardDescription>
          </div>
          
          <select 
            id="filter-source"
            v-model="selectedFilterSource" 
            @change="fetchMappings"
            class="border border-slate-200 rounded-lg px-3 py-1.5 text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white select-custom"
          >
            <option value="">全部来源</option>
            <option v-for="s in sources" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </CardHeader>
        <CardContent>
          <!-- Mappings Table -->
          <div class="overflow-hidden rounded-xl border border-slate-200/80">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50 text-slate-400 text-[10px] font-bold uppercase tracking-wider border-b border-slate-200/80">
                  <th class="p-4">数据分类</th>
                  <th class="p-4">目标标准字段</th>
                  <th class="p-4">Excel 原始列标题</th>
                  <th class="p-4 text-center">使用状态</th>
                  <th class="p-4 text-center">操作</th>
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
                    <span class="px-2.5 py-1 rounded-full text-[10px] font-semibold" :class="getSourceBadgeClass(m.data_source)">
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
                      @click="toggleActive(m)" 
                      variant="ghost"
                      size="xs"
                      class="px-2.5 py-1 rounded-full text-[10px] font-bold"
                      :class="m.is_active ? 'bg-emerald-50 text-emerald-600 hover:bg-emerald-100' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'"
                    >
                      <span class="w-1.5 h-1.5 rounded-full mr-1" :class="m.is_active ? 'bg-emerald-500' : 'bg-slate-400'"></span>
                      <span>{{ m.is_active ? '已启用' : '已禁用' }}</span>
                    </Button>
                  </td>
                  <td class="p-4 text-center">
                    <Button 
                      @click="deleteMapping(m.id)" 
                      variant="ghost"
                      size="xs"
                      class="text-rose-500 hover:text-rose-700 hover:bg-rose-50 font-bold"
                    >
                      🗑 删除
                    </Button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { api } from '../services/api';
import type { FieldMapping } from '../services/api';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Sliders, Plus, Trash2, FolderOpen } from 'lucide-vue-next';

const sources = [
  { value: 'tonglian', label: '通联后台', badge: 'bg-violet-50 text-violet-600' },
  { value: 'meituan', label: '美团收入', badge: 'bg-amber-50 text-amber-600' },
  { value: 'douyin', label: '抖音收入', badge: 'bg-slate-100 text-slate-700' },
  { value: 'cash', label: '现金收入', badge: 'bg-teal-50 text-teal-600' },
  { value: 'sales', label: '销售收入', badge: 'bg-blue-50 text-blue-600' },
];

const selectedFilterSource = ref('');
const mappings = ref<FieldMapping[]>([]);

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

const toggleActive = async (m: FieldMapping) => {
  try {
    await api.updateFieldMapping(m.id, { is_active: !m.is_active });
    fetchMappings();
  } catch (error) {
    alert('修改状态失败！');
  }
};

const deleteMapping = async (id: number) => {
  if (!confirm('确定删除此条列头配置吗？')) return;
  try {
    await api.deleteFieldMapping(id);
    fetchMappings();
  } catch (error) {
    alert('删除映射失败！');
  }
};

onMounted(() => {
  fetchMappings();
});
</script>
