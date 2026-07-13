<template>
  <div class="flex h-screen bg-slate-100 text-slate-800 font-sans overflow-hidden">
    <!-- Sidebar -->
    <aside class="w-64 bg-[#1e293b] text-white flex flex-col shadow-xl z-20">
      <!-- App title -->
      <div class="p-6 border-b border-slate-700/50 flex items-center gap-3">
        <div class="p-2 bg-blue-600 rounded-lg text-white shadow-lg shadow-blue-500/30">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 002 2h2a2 2 0 002-2z" />
          </svg>
        </div>
        <div>
          <h1 class="font-bold text-lg leading-tight tracking-wide">FRP 对账平台</h1>
          <span class="text-[10px] text-slate-400 font-medium tracking-wider uppercase">Reconciliation Platform</span>
        </div>
      </div>

      <!-- Navigation links -->
      <nav class="flex-1 px-4 py-6 space-y-1.5 overflow-y-auto">
        <router-link 
          to="/" 
          class="flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group text-slate-300 hover:text-white hover:bg-slate-800/60"
          active-class="bg-blue-600/90 text-white font-medium shadow-md shadow-blue-500/20 hover:bg-blue-600"
        >
          <span class="p-1 rounded-md group-hover:scale-110 transition-transform">📊</span>
          <span>系统看板</span>
        </router-link>

        <router-link 
          to="/import" 
          class="flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group text-slate-300 hover:text-white hover:bg-slate-800/60"
          active-class="bg-blue-600/90 text-white font-medium shadow-md shadow-blue-500/20 hover:bg-blue-600"
        >
          <span class="p-1 rounded-md group-hover:scale-110 transition-transform">📥</span>
          <span>文件导入</span>
        </router-link>

        <router-link 
          to="/reconciliation" 
          class="flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group text-slate-300 hover:text-white hover:bg-slate-800/60"
          active-class="bg-blue-600/90 text-white font-medium shadow-md shadow-blue-500/20 hover:bg-blue-600"
        >
          <span class="p-1 rounded-md group-hover:scale-110 transition-transform">🔍</span>
          <span>对账明细</span>
        </router-link>

        <!-- Divider -->
        <div class="h-px bg-slate-700/50 my-6 mx-2"></div>

        <div class="px-4 text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">系统配置</div>

        <router-link 
          to="/settings/mappings" 
          class="flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group text-slate-300 hover:text-white hover:bg-slate-800/60"
          active-class="bg-blue-600/90 text-white font-medium shadow-md shadow-blue-500/20 hover:bg-blue-600"
        >
          <span class="p-1 rounded-md group-hover:scale-110 transition-transform">⚙️</span>
          <span>字段映射</span>
        </router-link>

        <router-link 
          to="/settings/stores" 
          class="flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group text-slate-300 hover:text-white hover:bg-slate-800/60"
          active-class="bg-blue-600/90 text-white font-medium shadow-md shadow-blue-500/20 hover:bg-blue-600"
        >
          <span class="p-1 rounded-md group-hover:scale-110 transition-transform">🏪</span>
          <span>门店标准化</span>
        </router-link>
      </nav>

      <!-- Footer/Info -->
      <div class="p-4 border-t border-slate-700/50 bg-slate-900/30 text-xs text-slate-400 flex flex-col gap-1.5">
        <div class="flex items-center justify-between">
          <span>服务状态</span>
          <span class="flex h-2 w-2 relative">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
        </div>
        <div>对账引擎 V1.0 (MVP)</div>
      </div>
    </aside>

    <!-- Main Content Area -->
    <main class="flex-1 flex flex-col overflow-hidden">
      <!-- Header -->
      <header class="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-8 shadow-sm">
        <div class="flex items-center gap-3">
          <h2 class="font-semibold text-lg text-slate-800">{{ pageTitle }}</h2>
        </div>
        <div class="flex items-center gap-4 text-sm text-slate-500">
          <span>🕒 当前账期: {{ currentDate }}</span>
        </div>
      </header>

      <!-- Page Content -->
      <div class="flex-1 overflow-auto p-8 bg-slate-50">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" class="fade-in" />
          </transition>
        </router-view>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRoute } from 'vue-router';

const route = useRoute();

const pageTitle = computed(() => {
  switch (route.name) {
    case 'Dashboard':
      return '系统看板';
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

const currentDate = computed(() => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
});
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
