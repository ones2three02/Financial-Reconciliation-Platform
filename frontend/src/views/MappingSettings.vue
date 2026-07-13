<template>
  <div class="space-y-8 fade-in">
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <!-- Create Mapping Form Card -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 flex flex-col justify-between h-fit">
        <div class="space-y-5">
          <div>
            <h3 class="text-lg font-bold text-slate-800">新增字段映射</h3>
            <p class="text-xs text-slate-400">若第三方 Excel 模板调整或列名变更，可在此配置映射</p>
          </div>

          <div class="space-y-4">
            <!-- Source Selector -->
            <div class="flex flex-col gap-1.5">
              <label for="new-source" class="text-xs font-bold text-slate-500 uppercase tracking-wider">数据来源</label>
              <select 
                id="new-source"
                v-model="newMapping.data_source"
                class="border border-slate-200 rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              >
                <option v-for="s in sources" :key="s.value" :value="s.value">{{ s.label }}</option>
              </select>
            </div>

            <!-- Target Field Selector -->
            <div class="flex flex-col gap-1.5">
              <label for="new-target" class="text-xs font-bold text-slate-500 uppercase tracking-wider">标准系统字段</label>
              <select 
                id="new-target"
                v-model="newMapping.target_field"
                class="border border-slate-200 rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              >
                <option value="trade_date">交易日期 (trade_date)</option>
                <option value="store_name">门店名称 (store_name)</option>
                <option value="amount">交易金额 (amount)</option>
              </select>
            </div>

            <!-- Source Column Input -->
            <div class="flex flex-col gap-1.5">
              <label for="new-column" class="text-xs font-bold text-slate-500 uppercase tracking-wider">Excel列标题 (必须完全一致)</label>
              <input 
                id="new-column"
                type="text" 
                v-model="newMapping.source_column" 
                placeholder="例如: 终端门店 / 交易净额(元)"
                class="border border-slate-200 rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>

        <button 
          @click="saveMapping"
          class="w-full bg-blue-600 hover:bg-blue-700 text-white rounded-xl py-2.5 mt-6 text-sm font-semibold shadow-md shadow-blue-500/20 transition-all"
        >
          保存映射配置
        </button>
      </div>

      <!-- Mappings List Card -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 lg:col-span-2 space-y-6">
        <div class="flex items-center justify-between">
          <div>
            <h3 class="text-lg font-bold text-slate-800">已配置映射规则</h3>
            <p class="text-xs text-slate-400">目前系统支持的所有来源 Excel 列头匹配规则</p>
          </div>
          
          <select 
            id="filter-source"
            v-model="selectedFilterSource" 
            @change="fetchMappings"
            class="border border-slate-200 rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
          >
            <option value="">全部来源</option>
            <option v-for="s in sources" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </div>

        <!-- Mappings Table -->
        <div class="overflow-x-auto rounded-xl border border-slate-100">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-50 text-slate-400 text-xs font-semibold uppercase tracking-wider border-b border-slate-100">
                <th class="p-4">数据分类</th>
                <th class="p-4">标准字段</th>
                <th class="p-4">Excel 原始列标题</th>
                <th class="p-4 text-center">状态</th>
                <th class="p-4 text-center">操作</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-sm">
              <tr v-if="filteredMappings.length === 0">
                <td colspan="5" class="p-8 text-center text-slate-400 text-sm">暂无对应的列映射规则</td>
              </tr>
              <tr v-for="m in filteredMappings" :key="m.id" class="hover:bg-slate-50/50 transition-colors">
                <td class="p-4">
                  <span class="px-2.5 py-1 rounded-full text-xs font-medium" :class="getSourceBadgeClass(m.data_source)">
                    {{ getSourceLabel(m.data_source) }}
                  </span>
                </td>
                <td class="p-4 font-mono text-xs font-bold text-slate-700">
                  {{ m.target_field }}
                </td>
                <td class="p-4 font-semibold text-slate-800">{{ m.source_column }}</td>
                <td class="p-4 text-center">
                  <button 
                    @click="toggleActive(m)" 
                    class="px-2 py-1 rounded text-xs font-semibold"
                    :class="m.is_active ? 'bg-emerald-50 text-emerald-600' : 'bg-slate-100 text-slate-500'"
                  >
                    {{ m.is_active ? '启用中' : '已禁用' }}
                  </button>
                </td>
                <td class="p-4 text-center">
                  <button 
                    @click="deleteMapping(m.id)" 
                    class="text-xs font-semibold text-rose-600 hover:text-rose-800 transition-colors"
                  >
                    🗑 删除
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { api } from '../services/api';
import type { FieldMapping } from '../services/api';

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
