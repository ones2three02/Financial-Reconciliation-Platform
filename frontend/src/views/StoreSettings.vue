<template>
  <div class="space-y-8 fade-in">
    <!-- Top Tabs Selection -->
    <div class="flex border-b border-slate-200/80 gap-6">
      <button 
        @click="activeTab = 'stores'"
        class="pb-3 text-sm font-bold border-b-2 transition-all flex items-center gap-2 select-none"
        :class="activeTab === 'stores' ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-400 hover:text-slate-700'"
      >
        <StoreIcon class="w-4.5 h-4.5" />
        <span>标准门店管理</span>
      </button>
      <button 
        @click="activeTab = 'aliases'"
        class="pb-3 text-sm font-bold border-b-2 transition-all flex items-center gap-2 select-none"
        :class="activeTab === 'aliases' ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-400 hover:text-slate-700'"
      >
        <Link class="w-4.5 h-4.5" />
        <span>别名别称绑定</span>
      </button>
    </div>

    <!-- Tab 1: Standard Stores Management -->
    <div v-if="activeTab === 'stores'" class="space-y-6 fade-in">
      <Card class="shadow-sm border border-slate-200/80">
        <CardHeader class="flex flex-row items-center justify-between flex-wrap gap-4 pb-4">
          <div>
            <CardTitle class="flex items-center gap-2.5 text-base font-bold text-slate-800">
              <StoreIcon class="h-4.5 w-4.5 text-blue-500" />
              <span>标准门店名录</span>
            </CardTitle>
            <CardDescription>配置集团下属的标准门店基本信息与联系人，用于生成统一对账报表</CardDescription>
          </div>
          <Button 
            @click="openAddModal"
            class="bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs flex items-center gap-1.5 h-9"
          >
            <Plus class="w-4 h-4" />
            <span>新增标准门店</span>
          </Button>
        </CardHeader>
        <CardContent>
          <div class="overflow-hidden rounded-xl border border-slate-200/80">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50 text-slate-400 text-[10px] font-bold uppercase tracking-wider border-b border-slate-200/80">
                  <th class="p-4">门店编码</th>
                  <th class="p-4">标准门店名称</th>
                  <th class="p-4">所在区域</th>
                  <th class="p-4">店长/负责人</th>
                  <th class="p-4">联系电话</th>
                  <th class="p-4 text-center">状态</th>
                  <th class="p-4 text-center">操作</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs">
                <tr v-if="stores.length === 0">
                  <td colspan="7" class="p-12 text-center text-slate-400 font-medium">
                    <div class="flex flex-col items-center justify-center gap-2">
                      <FolderOpen class="w-8 h-8 text-slate-300" />
                      <span>暂无标准门店记录</span>
                    </div>
                  </td>
                </tr>
                <tr v-for="s in stores" :key="s.id" class="hover:bg-slate-50/40 transition-colors">
                  <td class="p-4 font-mono font-bold text-slate-500">{{ s.code || '—' }}</td>
                  <td class="p-4 font-extrabold text-slate-800">{{ s.name }}</td>
                  <td class="p-4 font-medium text-slate-600">{{ s.region || '—' }}</td>
                  <td class="p-4 font-medium text-slate-600">{{ s.manager || '—' }}</td>
                  <td class="p-4 font-mono text-slate-500">{{ s.phone || '—' }}</td>
                  <td class="p-4 text-center">
                    <button 
                      @click="toggleStoreStatus(s)" 
                      class="px-2.5 py-1 rounded-full text-[10px] font-bold inline-flex items-center gap-1 transition-all"
                      :class="s.is_active ? 'bg-emerald-50 text-emerald-600 hover:bg-emerald-100' : 'bg-slate-100 text-slate-400 hover:bg-slate-200'"
                      title="点击切换状态"
                    >
                      <span class="w-1.5 h-1.5 rounded-full" :class="s.is_active ? 'bg-emerald-500' : 'bg-slate-400'"></span>
                      <span>{{ s.is_active ? '运营中' : '已停用' }}</span>
                    </button>
                  </td>
                  <td class="p-4 text-center">
                    <div class="flex items-center justify-center gap-2" v-if="confirmDeleteStoreId !== s.id">
                      <Button 
                        @click="openEditModal(s)"
                        variant="ghost"
                        size="xs"
                        class="text-blue-600 hover:text-blue-800 hover:bg-blue-50 font-bold"
                      >
                        编辑
                      </Button>
                      <Button 
                        @click="confirmDeleteStoreId = s.id" 
                        variant="ghost"
                        size="xs"
                        class="text-rose-500 hover:text-rose-700 hover:bg-rose-50 font-bold"
                      >
                        删除
                      </Button>
                    </div>
                    <div v-else class="flex items-center gap-1.5 justify-center">
                      <Button @click="deleteStore(s.id)" size="xs" class="bg-rose-600 hover:bg-rose-700 text-white h-7 text-[10px] px-2 font-bold">确认</Button>
                      <Button @click="confirmDeleteStoreId = null" size="xs" variant="outline" class="h-7 text-[10px] px-2 font-bold">取消</Button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- Tab 2: Alias Standardization Mapping -->
    <div v-else-if="activeTab === 'aliases'" class="fade-in">
      <Card class="shadow-sm border border-slate-200/80">
        <CardHeader class="flex flex-row items-center justify-between flex-wrap gap-4 pb-4">
          <div>
            <CardTitle class="flex items-center gap-2.5 text-base font-bold text-slate-800">
              <Link class="h-4.5 w-4.5 text-blue-500" />
              <span>门店别名标准化</span>
            </CardTitle>
            <CardDescription>关联三方交易渠道 Excel 中的非标准别名到财务汇总标准店名</CardDescription>
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
                      class="w-full max-w-[250px] h-8"
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

    <!-- Store Add/Edit Modal Dialog -->
    <div 
      v-if="showEditModal" 
      class="fixed inset-0 bg-zinc-950/40 backdrop-blur-sm z-50 flex items-center justify-center p-4 fade-in"
      @click.self="showEditModal = false"
    >
      <Card class="w-full max-w-md shadow-2xl border border-slate-200/80 overflow-hidden bg-white">
        <CardHeader class="bg-slate-50/50 border-b border-slate-200/60 pb-4">
          <div class="flex items-center justify-between">
            <div>
              <CardTitle class="text-base font-bold text-slate-800">
                {{ formStore.id ? '编辑标准门店信息' : '新增标准门店' }}
              </CardTitle>
              <CardDescription class="text-xs text-slate-400">
                {{ formStore.id ? '更新标准名录下的门店配置基本资料' : '在名录中录入一家全新的标准门店' }}
              </CardDescription>
            </div>
            <button @click="showEditModal = false" class="text-slate-400 hover:text-slate-600 text-lg font-bold">×</button>
          </div>
        </CardHeader>
        
        <CardContent class="p-6 space-y-4">
          <!-- Store Name -->
          <div class="flex flex-col gap-1.5">
            <label for="store-name" class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">标准门店名称 (必填)</label>
            <Input 
              id="store-name"
              v-model="formStore.name" 
              placeholder="例如: 钟祥店"
              class="h-9 text-xs"
              required
            />
          </div>

          <!-- Store Code -->
          <div class="flex flex-col gap-1.5">
            <label for="store-code" class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">门店财务编码</label>
            <Input 
              id="store-code"
              v-model="formStore.code" 
              placeholder="例如: MD013"
              class="h-9 text-xs"
            />
          </div>

          <!-- Region -->
          <div class="flex flex-col gap-1.5">
            <label for="store-region" class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">所在运营区域</label>
            <Input 
              id="store-region"
              v-model="formStore.region" 
              placeholder="例如: 荆州地区"
              class="h-9 text-xs"
            />
          </div>

          <div class="grid grid-cols-2 gap-4">
            <!-- Manager -->
            <div class="flex flex-col gap-1.5">
              <label for="store-manager" class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">店长负责人</label>
              <Input 
                id="store-manager"
                v-model="formStore.manager" 
                placeholder="店长姓名"
                class="h-9 text-xs"
              />
            </div>

            <!-- Phone -->
            <div class="flex flex-col gap-1.5">
              <label for="store-phone" class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">联系电话</label>
              <Input 
                id="store-phone"
                v-model="formStore.phone" 
                placeholder="手机号码"
                class="h-9 text-xs"
              />
            </div>
          </div>

          <!-- Active status toggle -->
          <div class="flex items-center gap-2 pt-2">
            <input 
              id="store-active-cb"
              type="checkbox" 
              v-model="formStore.is_active" 
              class="rounded border-slate-300 text-blue-600 focus:ring-blue-500 w-4 h-4"
            />
            <label for="store-active-cb" class="text-xs font-bold text-slate-700 cursor-pointer">
              启用此门店运营状态
            </label>
          </div>
        </CardContent>

        <CardFooter class="bg-slate-50/50 border-t border-slate-200/60 p-4 flex justify-end gap-3">
          <Button 
            @click="showEditModal = false"
            variant="outline"
            size="sm"
            class="h-8 text-xs font-semibold"
          >
            取消
          </Button>
          <Button 
            @click="submitForm"
            size="sm"
            class="h-8 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs shadow-md shadow-blue-500/10 flex items-center gap-1.5"
          >
            <Save class="w-3.5 h-3.5" />
            <span>保存门店</span>
          </Button>
        </CardFooter>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { api } from '../services/api';
import type { Store, StoreAlias } from '../services/api';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Select } from '../components/ui/select';
import { Store as StoreIcon, Link, Plus, Trash2, CheckCircle2, FolderOpen, Save } from 'lucide-vue-next';

// Tab state
const activeTab = ref('stores'); // 'stores' or 'aliases'

// Data states
const stores = ref<Store[]>([]);
const aliases = ref<StoreAlias[]>([]);

// Delete confirmation states
const confirmDeleteStoreId = ref<number | null>(null);

// Alias filtering states
const aliasFilter = ref('pending');

// Modal Form states
const showEditModal = ref(false);
const formStore = ref({
  id: null as number | null,
  name: '',
  code: '',
  region: '',
  manager: '',
  phone: '',
  is_active: true
});

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

const openAddModal = () => {
  formStore.value = {
    id: null,
    name: '',
    code: '',
    region: '',
    manager: '',
    phone: '',
    is_active: true
  };
  showEditModal.value = true;
};

const openEditModal = (store: Store) => {
  formStore.value = {
    id: store.id,
    name: store.name,
    code: store.code || '',
    region: store.region || '',
    manager: store.manager || '',
    phone: store.phone || '',
    is_active: store.is_active
  };
  showEditModal.value = true;
};

const submitForm = async () => {
  if (!formStore.value.name.trim()) {
    alert('请输入门店名称！');
    return;
  }
  
  const payload = {
    name: formStore.value.name.trim(),
    code: formStore.value.code.trim() || undefined,
    region: formStore.value.region.trim() || undefined,
    manager: formStore.value.manager.trim() || undefined,
    phone: formStore.value.phone.trim() || undefined,
    is_active: formStore.value.is_active
  };

  try {
    if (formStore.value.id === null) {
      await api.createStore(payload);
    } else {
      await api.updateStore(formStore.value.id, payload);
    }
    showEditModal.value = false;
    fetchStores();
    fetchAliases();
  } catch (err: any) {
    alert(err.response?.data?.detail || '保存门店失败！');
  }
};

const toggleStoreStatus = async (store: Store) => {
  try {
    await api.updateStore(store.id, { is_active: !store.is_active });
    fetchStores();
  } catch (error) {
    alert('修改门店状态失败！');
  }
};

const deleteStore = async (id: number) => {
  try {
    await api.deleteStore(id);
    confirmDeleteStoreId.value = null;
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
