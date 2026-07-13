<template>
  <div class="flex h-screen bg-slate-50/50 text-slate-900 font-sans overflow-hidden">
    <!-- Sidebar -->
    <aside class="w-64 bg-zinc-950 text-zinc-400 flex flex-col border-r border-zinc-800 z-20">
      <!-- App Title Header -->
      <div class="h-16 px-6 border-b border-zinc-800 flex items-center gap-3">
        <div class="p-2 bg-blue-600 rounded-lg text-white shadow-lg shadow-blue-500/20">
          <Activity class="h-5 w-5" />
        </div>
        <div>
          <h1 class="font-bold text-sm text-zinc-50 leading-none tracking-wide">FRP 对账平台</h1>
          <span class="text-[9px] text-zinc-500 font-semibold tracking-widest uppercase">Reconciliation Platform</span>
        </div>
      </div>

      <!-- Navigation Links -->
      <nav class="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
        <div class="px-3 text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-3">系统导航</div>
        
        <router-link 
          to="/" 
          class="flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-150 group text-zinc-400 hover:text-zinc-50 hover:bg-zinc-900"
          active-class="bg-zinc-900 text-zinc-50 font-medium border border-zinc-800 shadow-sm"
        >
          <LayoutDashboard class="h-4 w-4 shrink-0 transition-transform group-hover:scale-105" />
          <span class="text-sm">系统看板</span>
        </router-link>

        <router-link 
          to="/import" 
          class="flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-150 group text-zinc-400 hover:text-zinc-50 hover:bg-zinc-900"
          active-class="bg-zinc-900 text-zinc-50 font-medium border border-zinc-800 shadow-sm"
        >
          <FileUp class="h-4 w-4 shrink-0 transition-transform group-hover:scale-105" />
          <span class="text-sm">文件导入</span>
        </router-link>

        <router-link 
          to="/reconciliation" 
          class="flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-150 group text-zinc-400 hover:text-zinc-50 hover:bg-zinc-900"
          active-class="bg-zinc-900 text-zinc-50 font-medium border border-zinc-800 shadow-sm"
        >
          <ClipboardCheck class="h-4 w-4 shrink-0 transition-transform group-hover:scale-105" />
          <span class="text-sm">对账明细</span>
        </router-link>

        <!-- Config Section -->
        <div class="h-px bg-zinc-800/80 my-5 mx-2"></div>
        <div class="px-3 text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-3">系统配置</div>

        <router-link 
          to="/settings/mappings" 
          class="flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-150 group text-zinc-400 hover:text-zinc-50 hover:bg-zinc-900"
          active-class="bg-zinc-900 text-zinc-50 font-medium border border-zinc-800 shadow-sm"
        >
          <Sliders class="h-4 w-4 shrink-0 transition-transform group-hover:scale-105" />
          <span class="text-sm">字段映射</span>
        </router-link>

        <router-link 
          to="/settings/stores" 
          class="flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-150 group text-zinc-400 hover:text-zinc-50 hover:bg-zinc-900"
          active-class="bg-zinc-900 text-zinc-50 font-medium border border-zinc-800 shadow-sm"
        >
          <Store class="h-4 w-4 shrink-0 transition-transform group-hover:scale-105" />
          <span class="text-sm">门店标准化</span>
        </router-link>
      </nav>

      <!-- Heartbeat Indicator -->
      <div class="p-4 border-t border-zinc-800 bg-zinc-950/20 text-xs text-zinc-500 flex flex-col gap-1.5">
        <div class="flex items-center justify-between">
          <span>对账服务引擎</span>
          <span class="flex h-2 w-2 relative">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
        </div>
        <div class="text-[10px] text-zinc-600">FRP Engine V1.0 (MVP)</div>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="flex-1 flex flex-col overflow-hidden">
      <!-- Header -->
      <header class="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-8 shadow-sm z-10">
        <div class="flex flex-col">
          <!-- Breadcrumbs -->
          <div class="text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
            <span>FRP Platform</span>
            <span>/</span>
            <span>{{ breadcrumbSection }}</span>
          </div>
          <h2 class="font-bold text-base text-slate-800 leading-tight mt-0.5">{{ pageTitle }}</h2>
        </div>
        <div class="flex items-center gap-4 text-xs font-semibold text-slate-500 bg-slate-50 border border-slate-200/80 rounded-lg px-3 py-1.5">
          <Calendar class="w-3.5 h-3.5 text-slate-400" />
          <span>当前账期: {{ currentDate }}</span>
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
import { computed } from 'vue';
import { useRoute } from 'vue-router';
import { LayoutDashboard, FileUp, ClipboardCheck, Sliders, Store, Calendar, Activity } from 'lucide-vue-next';

const route = useRoute();

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
