<template>
  <div v-if="isInitializing" class="h-screen w-screen bg-[#09090b] flex flex-col items-center justify-center text-zinc-100 font-sans select-none">
    <div class="p-3 bg-blue-600 rounded-2xl text-white shadow-2xl shadow-blue-500/20 mb-6 animate-pulse">
      <svg class="h-10 w-10" viewBox="0 0 256 256" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path fill="currentColor" fill-rule="evenodd" d="M48 38 H145 L207 91 V108 C207 145 180 166 138 166 H94 V218 H48 Z M94 78 V126 H136 C155 126 165 117 165 102 C165 87 155 78 136 78 Z M112 148 H160 L211 218 H158 L101 163 Z"/>
      </svg>
    </div>
    <h3 class="text-sm font-bold tracking-wider text-zinc-100">财务自动对账平台</h3>
    <p class="text-[10px] text-zinc-500 mt-2 font-medium tracking-wide animate-pulse">正在启动安全沙箱与本地计算服务，请稍候...</p>
  </div>
  <template v-else>
    <div v-if="route.path === '/login'" class="h-screen w-screen bg-[#09090b] flex items-center justify-center">
      <router-view />
    </div>
    <div v-else class="flex h-screen bg-slate-50/50 text-slate-900 font-sans overflow-hidden">
    <!-- Sidebar -->
    <aside 
      :class="[
        'bg-zinc-950 text-zinc-400 flex flex-col border-r border-zinc-800 z-20 transition-all duration-300 ease-in-out shrink-0 select-none',
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
        <div class="p-1.5 bg-blue-600 rounded-lg text-white shadow-lg shadow-blue-500/20 shrink-0">
          <svg class="h-6 w-6" viewBox="0 0 256 256" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path fill="currentColor" fill-rule="evenodd" d="M48 38 H145 L207 91 V108 C207 145 180 166 138 166 H94 V218 H48 Z M94 78 V126 H136 C155 126 165 117 165 102 C165 87 155 78 136 78 Z M112 148 H160 L211 218 H158 L101 163 Z"/>
          </svg>
        </div>
        <div v-if="!isCollapsed" class="fade-in transition-all duration-300">
          <h1 class="font-bold text-sm text-zinc-50 leading-none tracking-wide">FRP 对账平台</h1>
          <span class="text-[9px] text-zinc-500 font-semibold tracking-widest uppercase">Reconciliation Platform</span>
        </div>
      </div>

      <!-- Navigation Links -->
      <nav class="flex-1 px-3 py-6 space-y-1.5 overflow-y-auto">
        <div v-if="!isCollapsed" class="px-3 text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-3 transition-all fade-in">日常工作</div>
        
        <router-link 
          to="/" 
          class="flex items-center gap-3 rounded-lg transition-all duration-150 group text-zinc-400 hover:text-zinc-50 hover:bg-zinc-900 border border-transparent"
          :class="isCollapsed ? 'justify-center p-2.5 w-10 h-10 mx-auto' : 'px-3 py-2.5'"
          active-class="bg-zinc-900 text-zinc-50 font-medium border border-zinc-800 shadow-sm"
          :title="isCollapsed ? '工作台' : ''"
        >
          <LayoutDashboard class="h-4.5 w-4.5 shrink-0 transition-transform group-hover:scale-105" />
          <span v-if="!isCollapsed" class="text-sm transition-all fade-in">工作台</span>
        </router-link>

        <router-link 
          to="/import" 
          class="flex items-center gap-3 rounded-lg transition-all duration-150 group text-zinc-400 hover:text-zinc-50 hover:bg-zinc-900 border border-transparent"
          :class="isCollapsed ? 'justify-center p-2.5 w-10 h-10 mx-auto' : 'px-3 py-2.5'"
          active-class="bg-zinc-900 text-zinc-50 font-medium border border-zinc-800 shadow-sm"
          :title="isCollapsed ? '导入数据' : ''"
        >
          <FileUp class="h-4.5 w-4.5 shrink-0 transition-transform group-hover:scale-105" />
          <span v-if="!isCollapsed" class="text-sm transition-all fade-in">导入数据</span>
        </router-link>

        <router-link 
          to="/reconciliation" 
          class="flex items-center gap-3 rounded-lg transition-all duration-150 group text-zinc-400 hover:text-zinc-50 hover:bg-zinc-900 border border-transparent"
          :class="isCollapsed ? 'justify-center p-2.5 w-10 h-10 mx-auto' : 'px-3 py-2.5'"
          active-class="bg-zinc-900 text-zinc-50 font-medium border border-zinc-800 shadow-sm"
          :title="isCollapsed ? '对账结果' : ''"
        >
          <ClipboardCheck class="h-4.5 w-4.5 shrink-0 transition-transform group-hover:scale-105" />
          <span v-if="!isCollapsed" class="text-sm transition-all fade-in">对账结果</span>
        </router-link>

        <!-- Config Section -->
        <div v-if="isAdmin" class="h-px bg-zinc-800/80 my-5" :class="isCollapsed ? 'mx-1' : 'mx-2'"></div>
        <div v-if="isAdmin && !isCollapsed" class="px-3 text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-3 transition-all fade-in">数据配置</div>

        <router-link 
          v-if="isAdmin"
          to="/settings/stores"
          class="flex items-center gap-3 rounded-lg transition-all duration-150 group text-zinc-400 hover:text-zinc-50 hover:bg-zinc-900 border border-transparent"
          :class="isCollapsed ? 'justify-center p-2.5 w-10 h-10 mx-auto' : 'px-3 py-2.5'"
          active-class="bg-zinc-900 text-zinc-50 font-medium border border-zinc-800 shadow-sm"
          :title="isCollapsed ? '门店管理' : ''"
        >
          <Store class="h-4.5 w-4.5 shrink-0 transition-transform group-hover:scale-105" />
          <span v-if="!isCollapsed" class="text-sm transition-all fade-in">门店管理</span>
        </router-link>

        <router-link 
          v-if="isAdmin"
          to="/settings/mappings"
          class="flex items-center gap-3 rounded-lg transition-all duration-150 group text-zinc-400 hover:text-zinc-50 hover:bg-zinc-900 border border-transparent"
          :class="isCollapsed ? 'justify-center p-2.5 w-10 h-10 mx-auto' : 'px-3 py-2.5'"
          active-class="bg-zinc-900 text-zinc-50 font-medium border border-zinc-800 shadow-sm"
          :title="isCollapsed ? '字段映射' : ''"
        >
          <Sliders class="h-4.5 w-4.5 shrink-0 transition-transform group-hover:scale-105" />
          <span v-if="!isCollapsed" class="text-sm transition-all fade-in">字段映射</span>
        </router-link>
      </nav>

      <DesktopUpdater :collapsed="isCollapsed" />

      <!-- Heartbeat Indicator -->
      <div 
        :class="[
          'border-t border-zinc-800 bg-zinc-950/20 text-xs text-zinc-500 flex transition-all duration-300 ease-in-out shrink-0',
          isCollapsed ? 'p-4 justify-center items-center h-14' : 'p-4 items-center'
        ]"
      >
        <div class="flex items-center justify-between w-full" :class="isCollapsed ? 'justify-center' : ''">
          <span v-if="!isCollapsed">本地服务正常</span>
          <span class="flex h-2 w-2 relative shrink-0">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
        </div>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="flex-1 flex flex-col overflow-hidden">
      <!-- Header -->
      <header class="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-8 shadow-sm z-10 shrink-0 select-none">
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
          <!-- Operations Guide Onboarding Trigger Button -->
          <button 
            v-if="route.path !== '/login' && route.path !== '/register'"
            @click="handleStartTour"
            class="flex items-center gap-1.5 px-3 py-1.5 bg-blue-50 border border-blue-100 hover:bg-blue-100 hover:text-blue-700 text-blue-600 rounded-lg text-xs font-bold transition-all shadow-sm shadow-blue-500/5 select-none shrink-0"
            title="查看当前页面的操作指引"
          >
            <span>💡</span>
            <span>新手引导</span>
          </button>

          <!-- Shared Global Date Selector -->
          <div id="global-date-selector" class="flex items-center gap-2">
            <span class="text-xs font-semibold text-slate-400 select-none">全局账期:</span>
            <DatePicker v-model="globalDate" align="right" class="h-9" />
          </div>

          <!-- User profile Badge and safety logout -->
          <div class="flex items-center gap-2 border-l border-slate-200 pl-4">
            <div class="w-8 h-8 rounded-full bg-blue-50/80 border border-blue-200 text-blue-600 flex items-center justify-center font-extrabold text-xs shrink-0 select-none shadow-sm">
              {{ currentUsername ? currentUsername.charAt(0).toUpperCase() : 'A' }}
            </div>
            <div class="flex flex-col text-left shrink-0">
              <span class="text-xs font-bold text-slate-700 leading-none">{{ currentRole }} ({{ currentUsername }})</span>
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

    <!-- 全局新手指引操作向导遮罩与弹窗 -->
    <Teleport to="body">
      <div v-if="isTourActive && currentStep" class="fixed inset-0 z-[10000] pointer-events-none select-none">
        <!-- 拦截底层页面点击的透明垫片 -->
        <div class="fixed inset-0 z-[9998] pointer-events-auto bg-transparent" @click="closeTour"></div>
        
        <!-- SVG 聚光灯镂空遮罩，不带任何模糊，支持圆角裁剪，彻底解决 stacking context 问题 -->
        <svg class="fixed inset-0 w-full h-full z-[9999] pointer-events-none">
          <path 
            fill="rgba(9, 9, 11, 0.45)" 
            fill-rule="evenodd" 
            :d="maskPath"
          />
        </svg>

        <!-- 元素外围呼吸高亮框，置于遮罩上方 -->
        <div 
          v-if="spotlightRect"
          class="fixed border-2 border-blue-500/80 rounded-xl shadow-2xl transition-all duration-200 pointer-events-none z-[10001]"
          :style="borderStyle"
        ></div>

        <!-- 悬浮说明气泡卡片 -->
        <div 
          class="fixed z-[10002] w-72 bg-white border border-slate-200/80 rounded-2xl p-4 shadow-xl flex flex-col gap-3 pointer-events-auto text-slate-800 transition-all duration-300"
          :style="tooltipStyle"
        >
          <div class="flex items-center justify-between">
            <span class="text-[10px] font-extrabold text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full select-none">
              指引步骤 {{ currentStepIndex + 1 }} / {{ tourSteps.length }}
            </span>
            <button @click="closeTour" class="text-slate-400 hover:text-slate-600 font-bold text-xs p-1 rounded-lg hover:bg-slate-100 transition-colors">
              ✕
            </button>
          </div>
          
          <div class="space-y-1">
            <h4 class="font-extrabold text-slate-800 text-xs flex items-center gap-1.5">
              <span>💡</span> {{ currentStep.title }}
            </h4>
            <p class="text-[11px] text-slate-500 leading-relaxed font-medium">
              {{ currentStep.content }}
            </p>
          </div>
          
          <div class="flex items-center justify-between mt-1 pt-2 border-t border-slate-100">
            <button 
              @click="prevStep" 
              class="text-[10px] font-bold text-slate-500 hover:text-slate-800 disabled:opacity-30 p-1.5 rounded-lg hover:bg-slate-100 transition-colors"
              :disabled="currentStepIndex === 0"
            >
              上一步
            </button>
            <div class="flex gap-2">
              <button 
                @click="closeTour" 
                class="text-[10px] font-bold text-slate-400 hover:text-slate-600 p-1.5"
              >
                跳过
              </button>
              <button 
                @click="nextStep" 
                class="text-[10px] font-bold bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded-lg shadow-sm shadow-blue-500/10 transition-colors"
              >
                {{ currentStepIndex === tourSteps.length - 1 ? '我知道了' : '下一步' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
    <DownloadTracker />
  </div>
  </template>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import DownloadTracker from './components/DownloadTracker.vue';
import DesktopUpdater from './components/DesktopUpdater.vue';
import { getDesktopBackendConfig } from './services/desktopConnection';

const isInitializing = ref(true);
import { 
  isTourActive, 
  tourSteps, 
  currentStepIndex, 
  startTour, 
  closeTour 
} from './services/tour';
import { globalDate } from './services/store';
import { DatePicker } from './components/ui/date-picker';
import { api, clearSession, getSession } from './services/api';
import { 
  LayoutDashboard, 
  FileUp, 
  ClipboardCheck, 
  Sliders, 
  Store, 
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
  return getSession().username || '未登录';
});

const currentRole = computed(() => {
  const role = getSession().role;
  return role === 'admin' ? '管理员' : role === 'finance' ? '财务' : '只读用户';
});
const isAdmin = computed(() => getSession().role === 'admin');

const handleLogout = async () => {
  try {
    await api.logout();
  } finally {
    clearSession();
    router.push('/login');
  }
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

// 新手指引向导流程控制器逻辑
const currentStep = computed(() => tourSteps.value[currentStepIndex.value] ?? null);
const tooltipStyle = ref<Record<string, string>>({});
const spotlightRect = ref<{ x: number; y: number; w: number; h: number } | null>(null);

const maskPath = computed(() => {
  if (!spotlightRect.value) return '';
  const screenW = window.innerWidth;
  const screenH = window.innerHeight;
  const { x, y, w, h } = spotlightRect.value;
  const r = 12; // spotlight hole rounded corner radius
  
  // Outer screen rectangle (clockwise)
  const outer = `M 0 0 H ${screenW} V ${screenH} H 0 Z`;
  
  // Inner rounded rectangle cutout path
  const inner = `M ${x + r} ${y} H ${x + w - r} A ${r} ${r} 0 0 1 ${x + w} ${y + r} V ${y + h - r} A ${r} ${r} 0 0 1 ${x + w - r} ${y + h} H ${x + r} A ${r} ${r} 0 0 1 ${x} ${y + h - r} V ${y + r} A ${r} ${r} 0 0 1 ${x + r} ${y} Z`;
  
  return `${outer} ${inner}`;
});

const borderStyle = computed(() => {
  if (!spotlightRect.value) return {};
  const { x, y, w, h } = spotlightRect.value;
  return {
    top: `${y}px`,
    left: `${x}px`,
    width: `${w}px`,
    height: `${h}px`
  };
});

const updateSpotlight = () => {
  if (!currentStep.value) return;
  const selector = currentStep.value.targetSelector;
  const el = document.querySelector(selector) as HTMLElement;
  
  if (el) {
    // 改用 behavior: 'auto' 瞬间滚动定位，彻底根除平滑滚动过渡期计算的相对位移偏移（如截图3的问题）
    el.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'auto' });
    
    // 用 nextTick 确保 DOM 滚动完全就绪后，直接进行坐标提取
    nextTick(() => {
      const rect = el.getBoundingClientRect();
      const padding = 6;
      
      spotlightRect.value = {
        x: rect.left - padding,
        y: rect.top - padding,
        w: rect.width + padding * 2,
        h: rect.height + padding * 2
      };
      
      const viewportHeight = window.innerHeight;
      const viewportWidth = window.innerWidth;
      

      
      // 对于高度非常大（超过半屏）的表格等大型组件（如门店名录、映射配置表），直接将气泡卡片停靠在右下角，使用 bottom/right 定位，彻底解决被裁切问题
      if (rect.height > viewportHeight * 0.5) {
        tooltipStyle.value = {
          bottom: '24px',
          right: '24px',
          top: 'auto',
          left: 'auto',
          transform: 'none'
        };
      } else {
        // 默认布局：气泡在元素下方
        let top = rect.bottom + 16;
        let left = rect.left;
        
        // 若下方空间不足，则将气泡置于上方
        if (rect.bottom + 180 > viewportHeight) {
          top = rect.top - 180;
        }
        
        // 视口安全边界保护（彻底解决气泡超出屏幕上方或左右边缘被裁切的问题）
        if (top < 16) {
          top = 16;
        }
        if (top + 160 > viewportHeight) {
          top = viewportHeight - 176;
        }
        if (left < 16) {
          left = 16;
        }
        if (left + 288 > viewportWidth) {
          left = viewportWidth - 304;
        }
        
        tooltipStyle.value = {
          top: `${top}px`,
          left: `${left}px`,
          bottom: 'auto',
          right: 'auto',
          transform: 'none'
        };
      }
    });
  } else {
    spotlightRect.value = null;
    tooltipStyle.value = {
      top: '50%',
      left: '50%',
      bottom: 'auto',
      right: 'auto',
      transform: 'translate(-50%, -50%)'
    };
  }
};

watch([isTourActive, currentStepIndex], () => {
  if (isTourActive.value) {
    nextTick(() => {
      updateSpotlight();
    });
  } else {
    spotlightRect.value = null;
  }
});

// 监听路由改变自动销毁未完成指引
watch(() => route.path, () => {
  closeTour();
});

const handleResize = () => {
  if (isTourActive.value) {
    updateSpotlight();
  }
};

onMounted(async () => {
  window.addEventListener('resize', handleResize);
  window.addEventListener('scroll', handleResize, true);
  
  if (typeof window !== 'undefined' && (window as any).__TAURI__) {
    try {
      await getDesktopBackendConfig(window);
    } catch (err) {
      console.error('初始化本地服务失败:', err);
    } finally {
      isInitializing.value = false;
    }
  } else {
    isInitializing.value = false;
  }
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  window.removeEventListener('scroll', handleResize, true);
});

const nextStep = () => {
  if (currentStepIndex.value < tourSteps.value.length - 1) {
    currentStepIndex.value++;
  } else {
    closeTour();
  }
};

const prevStep = () => {
  if (currentStepIndex.value > 0) {
    currentStepIndex.value--;
  }
};

const handleStartTour = () => {
  const path = route.path;
  if (path === '/') startTour('dashboard');
  else if (path === '/reconciliation') startTour('reconciliation');
  else if (path === '/import') startTour('import');
  else if (path === '/settings/stores') startTour('stores');
  else if (path === '/settings/mappings') startTour('mappings');
};
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
