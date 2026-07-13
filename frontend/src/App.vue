<template>
  <div v-if="route.path === '/login'" class="h-screen w-screen bg-[#09090b] flex items-center justify-center">
    <router-view />
  </div>
  <div v-else class="flex h-screen bg-slate-50/50 text-slate-900 font-sans overflow-hidden">
    <!-- Sidebar -->
    <aside 
      :class="[
        'bg-zinc-950 text-zinc-400 flex flex-col border-r border-zinc-800 z-20 transition-all duration-300 ease-in-out shrink-0',
        isCollapsed ? 'w-16' : 'w-64'
      ]"
    >
      <!-- App Title Header -->
      <div 
        :class="[
          'h-16 border-b border-zinc-800 flex items-center gap-3 transition-all duration-300 ease-in-out shrink-0',
          isCollapsed ? 'px-4 justify-center' : 'px-6'
        ]"
      >
        <div class="p-2 bg-blue-600 rounded-lg text-white shadow-lg shadow-blue-500/20 shrink-0">
          <Activity class="h-5 w-5" />
        </div>
        <div v-if="!isCollapsed" class="fade-in transition-all duration-300">
          <h1 class="font-bold text-sm text-zinc-50 leading-none tracking-wide">FRP 对账平台</h1>
          <span class="text-[9px] text-zinc-500 font-semibold tracking-widest uppercase">Reconciliation Platform</span>
        </div>
      </div>

      <!-- Navigation Links -->
      <nav class="flex-1 px-3 py-6 space-y-1.5 overflow-y-auto">
        <div v-if="!isCollapsed" class="px-3 text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-3 transition-all fade-in">系统导航</div>
        
        <router-link 
          to="/" 
          class="flex items-center gap-3 rounded-lg transition-all duration-150 group text-zinc-400 hover:text-zinc-50 hover:bg-zinc-900"
          :class="isCollapsed ? 'justify-center p-2.5 w-10 h-10 mx-auto' : 'px-3 py-2.5'"
          active-class="bg-zinc-900 text-zinc-50 font-medium border border-zinc-800 shadow-sm"
          :title="isCollapsed ? '系统看板' : ''"
        >
          <LayoutDashboard class="h-4.5 w-4.5 shrink-0 transition-transform group-hover:scale-105" />
          <span v-if="!isCollapsed" class="text-sm transition-all fade-in">系统看板</span>
        </router-link>

        <router-link 
          to="/import" 
          class="flex items-center gap-3 rounded-lg transition-all duration-150 group text-zinc-400 hover:text-zinc-50 hover:bg-zinc-900"
          :class="isCollapsed ? 'justify-center p-2.5 w-10 h-10 mx-auto' : 'px-3 py-2.5'"
          active-class="bg-zinc-900 text-zinc-50 font-medium border border-zinc-800 shadow-sm"
          :title="isCollapsed ? '文件导入' : ''"
        >
          <FileUp class="h-4.5 w-4.5 shrink-0 transition-transform group-hover:scale-105" />
          <span v-if="!isCollapsed" class="text-sm transition-all fade-in">文件导入</span>
        </router-link>

        <router-link 
          to="/reconciliation" 
          class="flex items-center gap-3 rounded-lg transition-all duration-150 group text-zinc-400 hover:text-zinc-50 hover:bg-zinc-900"
          :class="isCollapsed ? 'justify-center p-2.5 w-10 h-10 mx-auto' : 'px-3 py-2.5'"
          active-class="bg-zinc-900 text-zinc-50 font-medium border border-zinc-800 shadow-sm"
          :title="isCollapsed ? '对账明细' : ''"
        >
          <ClipboardCheck class="h-4.5 w-4.5 shrink-0 transition-transform group-hover:scale-105" />
          <span v-if="!isCollapsed" class="text-sm transition-all fade-in">对账明细</span>
        </router-link>

        <!-- Config Section -->
        <div class="h-px bg-zinc-800/80 my-5" :class="isCollapsed ? 'mx-1' : 'mx-2'"></div>
        <div v-if="!isCollapsed" class="px-3 text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-3 transition-all fade-in">系统配置</div>

        <router-link 
          to="/settings/mappings" 
          class="flex items-center gap-3 rounded-lg transition-all duration-150 group text-zinc-400 hover:text-zinc-50 hover:bg-zinc-900"
          :class="isCollapsed ? 'justify-center p-2.5 w-10 h-10 mx-auto' : 'px-3 py-2.5'"
          active-class="bg-zinc-900 text-zinc-50 font-medium border border-zinc-800 shadow-sm"
          :title="isCollapsed ? '字段映射' : ''"
        >
          <Sliders class="h-4.5 w-4.5 shrink-0 transition-transform group-hover:scale-105" />
          <span v-if="!isCollapsed" class="text-sm transition-all fade-in">字段映射</span>
        </router-link>

        <router-link 
          to="/settings/stores" 
          class="flex items-center gap-3 rounded-lg transition-all duration-150 group text-zinc-400 hover:text-zinc-50 hover:bg-zinc-900"
          :class="isCollapsed ? 'justify-center p-2.5 w-10 h-10 mx-auto' : 'px-3 py-2.5'"
          active-class="bg-zinc-900 text-zinc-50 font-medium border border-zinc-800 shadow-sm"
          :title="isCollapsed ? '门店标准化' : ''"
        >
          <Store class="h-4.5 w-4.5 shrink-0 transition-transform group-hover:scale-105" />
          <span v-if="!isCollapsed" class="text-sm transition-all fade-in">门店标准化</span>
        </router-link>
      </nav>

      <!-- Heartbeat Indicator -->
      <div 
        :class="[
          'border-t border-zinc-800 bg-zinc-950/20 text-xs text-zinc-500 flex transition-all duration-300 ease-in-out shrink-0',
          isCollapsed ? 'p-4 justify-center items-center h-14' : 'p-4 flex-col gap-1.5'
        ]"
      >
        <div class="flex items-center justify-between w-full" :class="isCollapsed ? 'justify-center' : ''">
          <span v-if="!isCollapsed">对账服务引擎</span>
          <span class="flex h-2 w-2 relative shrink-0">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
        </div>
        <div v-if="!isCollapsed" class="text-[10px] text-zinc-600 fade-in">FRP Engine V1.0 (MVP)</div>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="flex-1 flex flex-col overflow-hidden">
      <!-- Header -->
      <header class="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-8 shadow-sm z-10 shrink-0">
        <div class="flex items-center gap-4">
          <!-- Sidebar Toggle Button -->
          <button 
            @click="toggleSidebar" 
            class="p-1.5 hover:bg-slate-100 rounded-lg text-slate-500 hover:text-slate-800 transition-colors border border-slate-200/50 shadow-sm bg-white shrink-0 flex items-center justify-center"
            :title="isCollapsed ? '展开菜单栏' : '收起菜单栏'"
          >
            <PanelLeftOpen class="w-4 h-4" v-if="isCollapsed" />
            <PanelLeftClose class="w-4 h-4" v-else />
          </button>
          
          <div class="flex flex-col">
            <!-- Breadcrumbs -->
            <div class="text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
              <span>FRP Platform</span>
              <span>/</span>
              <span>{{ breadcrumbSection }}</span>
            </div>
            <h2 class="font-bold text-base text-slate-800 leading-tight mt-0.5">{{ pageTitle }}</h2>
          </div>
        </div>
        
        <!-- Header Right side details -->
        <div class="flex items-center gap-4 shrink-0">
          <div class="flex items-center gap-2 text-xs font-semibold text-slate-500 bg-slate-50 border border-slate-200/80 rounded-lg px-3 py-1.5">
            <Calendar class="w-3.5 h-3.5 text-slate-400" />
            <span>当前账期: {{ currentDate }}</span>
          </div>

          <!-- User profile Badge and safety logout -->
          <div class="flex items-center gap-2 border-l border-slate-200 pl-4">
            <div class="w-8 h-8 rounded-full bg-blue-50/80 border border-blue-200 text-blue-600 flex items-center justify-center font-extrabold text-xs shrink-0 select-none shadow-sm">
              {{ currentUsername ? currentUsername.charAt(0).toUpperCase() : 'A' }}
            </div>
            <div class="flex flex-col text-left shrink-0">
              <span class="text-xs font-bold text-slate-700 leading-none">管理员 ({{ currentUsername }})</span>
              <button 
                @click="handleLogout" 
                class="text-[10px] text-slate-400 font-bold hover:text-rose-500 hover:underline transition-all mt-0.5 text-left bg-transparent p-0 border-0"
              >
                安全退出
              </button>
            </div>
          </div>
        </div>
      </header>

      <!-- Views Container -->
      <div class="flex-1 overflow-auto p-8 bg-slate-50/50">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { 
  LayoutDashboard, 
  FileUp, 
  ClipboardCheck, 
  Sliders, 
  Store, 
  Calendar, 
  Activity, 
  PanelLeftClose, 
  PanelLeftOpen 
} from 'lucide-vue-next';

const route = useRoute();
const router = useRouter();

// Persist sidebar state in localStorage
const isCollapsed = ref(localStorage.getItem('sidebar-collapsed') === 'true');

const toggleSidebar = () => {
  isCollapsed.value = !isCollapsed.value;
  localStorage.setItem('sidebar-collapsed', String(isCollapsed.value));
};

const currentUsername = computed(() => {
  return localStorage.getItem('username') || 'admin';
});

const handleLogout = () => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('username');
  router.push('/login');
};

const pageTitle = computed(() => {
  switch (route.name) {
    case 'Dashboard':
      return '数据统计大屏';
    case 'ImportCenter':
      return '文件导入中心';
    case 'ReconciliationList':
      return '财务对账明细';
    case 'MappingSettings':
      return '字段映射配置';
    case 'StoreSettings':
      return '门店标准化中心';
    default:
      return '财务自动对账平台';
  }
});

const breadcrumbSection = computed(() => {
  switch (route.name) {
    case 'Dashboard':
      return '看板';
    case 'ImportCenter':
      return '数据采集';
    case 'ReconciliationList':
      return '对账结果';
    case 'MappingSettings':
    case 'StoreSettings':
      return '配置中心';
    default:
      return '核心系统';
  }
});

const currentDate = computed(() => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
});
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.1s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
