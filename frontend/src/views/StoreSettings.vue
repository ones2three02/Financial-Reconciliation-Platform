<template>
  <div class="space-y-8 fade-in">
    <!-- Two Column Layout: Standard Stores & Aliases mapping -->
    <div class="grid grid-cols-1 xl:grid-cols-3 gap-8">
      
      <!-- Standard Stores Management (Left Column) -->
      <Card class="h-fit shadow-sm border border-slate-200/80">
        <CardHeader class="pb-4">
          <CardTitle class="flex items-center gap-2.5 text-base font-bold text-slate-800">
            <StoreIcon class="h-4.5 w-4.5 text-blue-500" />
            <span>标准门店名录</span>
          </CardTitle>
          <CardDescription>定义唯一的财务汇总标准门店名称</CardDescription>
        </CardHeader>
        <CardContent class="space-y-5">
          <!-- Add Store Form -->
          <div class="flex items-center gap-2">
            <Input 
              id="new-store-name"
              v-model="newStoreName" 
              placeholder="例如: 杨一一店"
              class="h-9 text-xs"
              @keyup.enter="saveStore"
            />
            <Button 
              @click="saveStore"
              size="sm"
              class="shrink-0 h-9 flex items-center gap-1 bg-blue-600 hover:bg-blue-700 text-white font-medium"
            >
              <Plus class="w-3.5 h-3.5" />
              <span>添加</span>
            </Button>
          </div>

          <!-- Store List -->
          <div class="max-h-[350px] overflow-y-auto pr-1 text-xs space-y-2">
            <div 
              v-if="stores.length === 0" 
              class="py-8 flex flex-col items-center justify-center text-slate-400 gap-1.5 border border-dashed border-slate-200 rounded-xl bg-slate-50/50"
            >
              <FolderOpen class="w-6 h-6 text-slate-300" />
              <span>暂无标准门店记录</span>
            </div>
            
            <div 
              v-for="s in stores" 
              :key="s.id"
              class="px-3.5 py-2.5 bg-white border border-slate-100 hover:border-slate-200 rounded-xl flex items-center justify-between group transition-all duration-150 hover:shadow-sm"
            >
              <div class="flex items-center gap-2.5">
                <div class="w-2 h-2 rounded-full bg-blue-500/80"></div>
                <span class="font-bold text-slate-700">{{ s.name }}</span>
              </div>
              <Button 
                @click="deleteStore(s.id)" 
                variant="ghost"
                size="xs"
                class="text-rose-500 hover:text-rose-700 hover:bg-rose-50 opacity-0 group-hover:opacity-100 transition-all font-semibold rounded-lg h-7 w-7 p-0 flex items-center justify-center"
              >
                <Trash2 class="w-3.5 h-3.5" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <!-- Store Aliases Binding (Right Columns) -->
      <Card class="xl:col-span-2 shadow-sm border border-slate-200/80">
        <CardHeader class="flex flex-row items-center justify-between flex-wrap gap-4 pb-4">
          <div>
            <CardTitle class="flex items-center gap-2.5 text-base font-bold text-slate-800">
              <Link class="h-4.5 w-4.5 text-blue-500" />
              <span>门店别名标准化</span>
            </CardTitle>
            <CardDescription>关联来自三方 Excel 的非标准化店名到财务标准店名</CardDescription>
          </div>

          <!-- Filters -->
          <div class="flex items-center gap-3">
            <label class="text-xs font-semibold text-slate-400 uppercase tracking-wider shrink-0">过滤别名</label>
            <Select 
              v-model="aliasFilter" 
              :options="filterOptions"
              @change="fetchAliases"
              class="w-36 h-9"
              align="right"
            />
          </div>
        </CardHeader>
        <CardContent>
          <!-- Alias Mapping Table -->
          <div class="overflow-hidden rounded-xl border border-slate-200/80">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50 text-slate-400 text-[10px] font-bold uppercase tracking-wider border-b border-slate-200/80">
                  <th class="p-4">Excel 中的原始店名</th>
                  <th class="p-4">对应标准门店</th>
                  <th class="p-4 text-center">状态</th>
                  <th class="p-4 text-center">更新操作</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs">
                <tr v-if="aliases.length === 0">
                  <td colspan="4" class="p-8 text-center text-slate-400 font-medium">
                    <div class="flex flex-col items-center justify-center gap-2">
                      <FolderOpen class="w-8 h-8 text-slate-300" />
                      <span>无需要配置的原始别名记录</span>
                    </div>
                  </td>
                </tr>
                <tr 
                  v-for="a in aliases" 
                  :key="a.id"
                  class="hover:bg-slate-50/40 transition-colors"
                  :class="{'bg-amber-50/10': a.status === 'pending'}"
                >
                  <td class="p-4 font-bold text-slate-700">{{ a.alias_name }}</td>
                  <td class="p-4">
                    <!-- Custom Select component -->
                    <Select 
                      v-model="a.store_id"
                      :options="storeOptions"
                      @change="mapAlias(a.id, a.store_id)"
                      class="w-full max-w-[200px] h-8"
                    />
                  </td>
                  <td class="p-4 text-center">
                    <span 
                      class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-semibold"
                      :class="a.status === 'mapped' ? 'bg-emerald-50 text-emerald-600' : 'bg-amber-50 text-amber-600'"
                    >
                      <span class="w-1.5 h-1.5 rounded-full" :class="a.status === 'mapped' ? 'bg-emerald-500' : 'bg-amber-500'"></span>
                      <span>{{ a.status === 'mapped' ? '已绑定' : '待财务核认' }}</span>
                    </span>
                  </td>
                  <td class="p-4 text-center">
                    <Button 
                      v-if="a.status === 'pending'"
                      @click="mapAlias(a.id, a.store_id)" 
                      size="xs"
                      :disabled="!a.store_id"
                      class="h-7 px-2.5 bg-blue-600 hover:bg-blue-700 text-white font-medium inline-flex items-center gap-1"
                    >
                      <CheckCircle2 class="w-3.5 h-3.5" />
                      <span>确认绑定</span>
                    </Button>
                    <span v-else class="text-xs text-slate-400 font-semibold inline-flex items-center gap-1">
                      <CheckCircle2 class="w-3.5 h-3.5 text-emerald-500" />
                      <span>已同步</span>
                    </span>
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
import type { Store, StoreAlias } from '../services/api';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Select } from '../components/ui/select';
import { Store as StoreIcon, Link, Plus, Trash2, CheckCircle2, FolderOpen } from 'lucide-vue-next';

const stores = ref<Store[]>([]);
const aliases = ref<StoreAlias[]>([]);
const newStoreName = ref('');
const aliasFilter = ref('pending'); // Default to show pending mappings first

const filterOptions = [
  { value: '', label: '全部别名' },
  { value: 'pending', label: '待核认 / 待匹配' },
  { value: 'mapped', label: '已绑定映射' }
];

const storeOptions = computed(() => {
  return [
    { value: null, label: '-- 请选择标准店名 (待认领) --' },
    ...stores.value.map(s => ({ value: s.id, label: s.name }))
  ];
});

const fetchStores = async () => {
  try {
    stores.value = await api.getStores();
  } catch (error) {
    console.error('Failed to load stores:', error);
  }
};

const fetchAliases = async () => {
  try {
    aliases.value = await api.getStoreAliases(aliasFilter.value || undefined);
  } catch (error) {
    console.error('Failed to load aliases:', error);
  }
};

const saveStore = async () => {
  if (!newStoreName.value.trim()) {
    alert('请输入门店名称！');
    return;
  }
  
  try {
    await api.createStore(newStoreName.value.trim());
    newStoreName.value = '';
    fetchStores();
    fetchAliases();
  } catch (err: any) {
    alert(err.response?.data?.detail || '创建门店失败！');
  }
};

const deleteStore = async (id: number) => {
  if (!confirm('确定删除此标准门店吗？其绑定的所有别名关系也将被解绑！')) return;
  try {
    await api.deleteStore(id);
    fetchStores();
    fetchAliases();
  } catch (error) {
    alert('删除门店失败！');
  }
};

const mapAlias = async (aliasId: number, storeId: number | null) => {
  try {
    await api.updateStoreAlias(aliasId, { store_id: storeId });
    fetchAliases();
  } catch (error) {
    alert('绑定别名失败！');
  }
};

onMounted(() => {
  fetchStores();
  fetchAliases();
});
</script>
