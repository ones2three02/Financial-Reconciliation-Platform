<template>
  <div class="space-y-8 fade-in">
    <!-- Two Column Layout: Standard Stores & Aliases mapping -->
    <div class="grid grid-cols-1 xl:grid-cols-3 gap-8">
      
      <!-- Standard Stores Management (Left Column) -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 flex flex-col justify-between h-fit">
        <div class="space-y-6">
          <div>
            <h3 class="text-lg font-bold text-slate-800">标准门店名录</h3>
            <p class="text-xs text-slate-400">定义唯一的财务汇总标准门店名称</p>
          </div>

          <!-- Add Store Form -->
          <div class="flex items-center gap-2">
            <input 
              id="new-store-name"
              type="text" 
              v-model="newStoreName" 
              placeholder="例如: 杨一一店"
              class="flex-1 border border-slate-200 rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              @keyup.enter="saveStore"
            />
            <button 
              @click="saveStore"
              class="px-4 py-2 bg-blue-600 text-white rounded-xl text-sm font-semibold hover:bg-blue-700 transition-colors shrink-0"
            >
              添加
            </button>
          </div>

          <!-- Store List -->
          <div class="divide-y divide-slate-100 max-h-[350px] overflow-y-auto pr-1 text-sm">
            <div v-if="stores.length === 0" class="py-4 text-center text-slate-400 text-sm">暂无标准门店记录</div>
            <div 
              v-for="s in stores" 
              :key="s.id"
              class="py-3 flex items-center justify-between group"
            >
              <div class="flex items-center gap-2">
                <span>🏪</span>
                <span class="font-semibold text-slate-700">{{ s.name }}</span>
              </div>
              <button 
                @click="deleteStore(s.id)" 
                class="text-xs text-rose-500 hover:text-rose-700 opacity-0 group-hover:opacity-100 transition-all font-semibold"
              >
                🗑 删除
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Store Aliases Binding (Right Columns) -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 xl:col-span-2 space-y-6">
        <div class="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h3 class="text-lg font-bold text-slate-800">门店别名标准化</h3>
            <p class="text-xs text-slate-400">关联来自三方 Excel 的非标准化店名到财务标准店名</p>
          </div>

          <!-- Filters -->
          <div class="flex items-center gap-3">
            <label for="alias-filter-select" class="text-xs font-semibold text-slate-500 uppercase tracking-wider">过滤别名</label>
            <select 
              id="alias-filter-select"
              v-model="aliasFilter" 
              @change="fetchAliases"
              class="border border-slate-200 rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
            >
              <option value="">全部别名</option>
              <option value="pending">待认领 / 待匹配</option>
              <option value="mapped">已绑定映射</option>
            </select>
          </div>
        </div>

        <!-- Alias Mapping Table -->
        <div class="overflow-x-auto rounded-xl border border-slate-100">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-50 text-slate-400 text-xs font-semibold uppercase tracking-wider border-b border-slate-100">
                <th class="p-4">Excel 中的原始店名</th>
                <th class="p-4">对应标准门店</th>
                <th class="p-4 text-center">状态</th>
                <th class="p-4 text-center">更新操作</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-sm">
              <tr v-if="aliases.length === 0">
                <td colspan="4" class="p-8 text-center text-slate-400 text-sm">无需要配置的原始别名记录</td>
              </tr>
              <tr 
                v-for="a in aliases" 
                :key="a.id"
                class="hover:bg-slate-50/50 transition-colors"
                :class="{'bg-amber-50/20': a.status === 'pending'}"
              >
                <td class="p-4 font-bold text-slate-700">{{ a.alias_name }}</td>
                <td class="p-4">
                  <!-- Mapped Select component -->
                  <select 
                    v-model="a.store_id"
                    class="border border-slate-200 rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white w-full max-w-[200px]"
                    @change="mapAlias(a.id, a.store_id)"
                  >
                    <option :value="null">-- 请选择标准店名 (待认领) --</option>
                    <option v-for="s in stores" :key="s.id" :value="s.id">{{ s.name }}</option>
                  </select>
                </td>
                <td class="p-4 text-center">
                  <span 
                    class="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider"
                    :class="a.status === 'mapped' ? 'bg-emerald-50 text-emerald-600' : 'bg-amber-50 text-amber-600'"
                  >
                    {{ a.status === 'mapped' ? '已绑定' : '待财务核认' }}
                  </span>
                </td>
                <td class="p-4 text-center">
                  <button 
                    v-if="a.status === 'pending'"
                    @click="mapAlias(a.id, a.store_id)" 
                    class="text-xs font-semibold text-blue-600 hover:text-blue-800 disabled:opacity-50"
                    :disabled="!a.store_id"
                  >
                    ✓ 确认绑定
                  </button>
                  <span v-else class="text-xs text-slate-400 font-medium">绑定完成</span>
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
import { ref, onMounted } from 'vue';
import { api } from '../services/api';
import type { Store, StoreAlias } from '../services/api';

const stores = ref<Store[]>([]);
const aliases = ref<StoreAlias[]>([]);
const newStoreName = ref('');
const aliasFilter = ref('pending'); // Default to show pending mappings first

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
    // After creating a store, refetch aliases as some pending alias might have been auto-bound
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
