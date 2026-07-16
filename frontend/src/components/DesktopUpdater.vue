<template>
  <div v-if="state.phase !== 'unsupported'" class="shrink-0 border-t border-zinc-800 px-3 py-3">
    <div
      v-if="!collapsed"
      class="px-3 pb-2 text-[10px] font-bold uppercase tracking-widest text-zinc-500"
    >
      桌面应用
    </div>
    <button
      type="button"
      :disabled="isBusy"
      :title="collapsed ? updateButtonLabel : ''"
      class="group relative flex items-center rounded-lg border border-transparent text-zinc-400 transition-all duration-150 hover:border-zinc-800 hover:bg-zinc-900 hover:text-zinc-50 disabled:cursor-wait disabled:opacity-70"
      :class="collapsed ? 'mx-auto h-10 w-10 justify-center p-2.5' : 'w-full gap-3 px-3 py-2.5'"
      @click="handleCheck"
    >
      <RefreshCw class="h-4.5 w-4.5 shrink-0" :class="state.phase === 'checking' ? 'animate-spin text-blue-400' : ''" />
      <span
        v-if="state.phase === 'available'"
        class="absolute h-2 w-2 rounded-full border-2 border-zinc-950 bg-blue-500"
        :class="collapsed ? 'right-1.5 top-1.5' : 'left-6 top-2'"
      ></span>
      <template v-if="!collapsed">
        <span class="text-sm">{{ updateButtonLabel }}</span>
        <span v-if="currentVersion" class="ml-auto text-[10px] font-semibold text-zinc-600">
          v{{ currentVersion }}
        </span>
      </template>
    </button>
  </div>

  <Teleport to="body">
    <div
      v-if="modalVisible"
      class="fixed inset-0 z-[11000] flex items-center justify-center bg-zinc-950/45 p-4 backdrop-blur-sm"
      @click.self="handleClose"
    >
      <div class="w-full max-w-lg overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl">
        <div class="flex items-start gap-3 border-b border-slate-100 px-6 py-5">
          <div class="mt-0.5 rounded-xl p-2.5" :class="headerIconClass">
            <CircleCheck v-if="state.phase === 'up_to_date'" class="h-5 w-5" />
            <TriangleAlert v-else-if="state.phase === 'error'" class="h-5 w-5" />
            <ShieldCheck v-else-if="state.phase === 'installing'" class="h-5 w-5" />
            <Download v-else class="h-5 w-5" />
          </div>
          <div class="min-w-0 flex-1">
            <h3 class="text-base font-extrabold text-slate-900">{{ modalTitle }}</h3>
            <p class="mt-1 text-xs leading-relaxed text-slate-500">{{ modalDescription }}</p>
          </div>
          <button
            v-if="!isBusy"
            type="button"
            class="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700"
            title="关闭"
            @click="handleClose"
          >
            <X class="h-4 w-4" />
          </button>
        </div>

        <div class="space-y-4 px-6 py-5">
          <div v-if="state.phase === 'available'" class="space-y-4">
            <div class="flex items-center gap-3 text-sm">
              <span class="rounded-lg bg-slate-100 px-3 py-1.5 font-bold text-slate-500">v{{ state.currentVersion }}</span>
              <ArrowRight class="h-4 w-4 text-blue-500" />
              <span class="rounded-lg bg-blue-50 px-3 py-1.5 font-extrabold text-blue-700">v{{ state.manifest.version }}</span>
              <span v-if="formattedReleaseDate" class="ml-auto text-[10px] font-semibold text-slate-400">
                {{ formattedReleaseDate }}
              </span>
            </div>
            <div class="max-h-52 overflow-auto whitespace-pre-wrap rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs leading-6 text-slate-600">
              {{ state.manifest.body || '本次更新未提供发布说明。' }}
            </div>
          </div>

          <div v-else-if="state.phase === 'up_to_date'" class="rounded-xl border border-emerald-100 bg-emerald-50 p-4 text-sm text-emerald-800">
            当前安装版本：<strong>v{{ state.currentVersion }}</strong>
          </div>

          <div v-else-if="state.phase === 'downloading'" class="space-y-3">
            <div class="flex items-center justify-between text-xs font-semibold text-slate-500">
              <span>正在下载签名更新包</span>
              <span>{{ progressLabel }}</span>
            </div>
            <div class="h-2.5 overflow-hidden rounded-full bg-slate-100">
              <div
                v-if="state.percent !== null"
                class="h-full rounded-full bg-blue-600 transition-all duration-200"
                :style="{ width: `${state.percent}%` }"
              ></div>
              <div v-else class="h-full w-1/3 animate-pulse rounded-full bg-blue-500"></div>
            </div>
            <p class="text-[11px] text-slate-400">下载完成后会自动校验签名并启动覆盖安装。</p>
          </div>

          <div v-else-if="state.phase === 'installing'" class="rounded-xl border border-blue-100 bg-blue-50 p-4 text-sm leading-6 text-blue-800">
            更新包已下载，正在校验并安装。Windows 安装程序完成后，应用将自动重新启动。
          </div>

          <div v-else-if="state.phase === 'error'" class="rounded-xl border border-rose-100 bg-rose-50 p-4 text-sm leading-6 text-rose-700">
            {{ state.message }}
          </div>
        </div>

        <div class="flex justify-end gap-3 border-t border-slate-100 bg-slate-50/70 px-6 py-4">
          <template v-if="state.phase === 'available'">
            <button type="button" class="rounded-lg border border-slate-200 bg-white px-4 py-2 text-xs font-bold text-slate-600 hover:bg-slate-50" @click="handleClose">
              暂不更新
            </button>
            <button type="button" class="rounded-lg bg-blue-600 px-4 py-2 text-xs font-bold text-white shadow-sm hover:bg-blue-700" @click="handleInstall">
              下载并安装
            </button>
          </template>
          <button
            v-else-if="state.phase === 'up_to_date'"
            type="button"
            class="rounded-lg bg-slate-900 px-4 py-2 text-xs font-bold text-white hover:bg-slate-800"
            @click="handleClose"
          >
            知道了
          </button>
          <template v-else-if="state.phase === 'error'">
            <button type="button" class="rounded-lg border border-slate-200 bg-white px-4 py-2 text-xs font-bold text-slate-600 hover:bg-slate-50" @click="handleClose">
              取消
            </button>
            <button type="button" class="rounded-lg bg-blue-600 px-4 py-2 text-xs font-bold text-white hover:bg-blue-700" @click="handleRetry">
              重试
            </button>
          </template>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, shallowRef } from 'vue';
import {
  ArrowRight,
  CircleCheck,
  Download,
  RefreshCw,
  ShieldCheck,
  TriangleAlert,
  X,
} from 'lucide-vue-next';

import {
  checkForDesktopUpdate,
  desktopUpdateErrorMessage,
  getCurrentDesktopVersion,
  installDesktopUpdate,
  isWindowsDesktop,
  type DesktopUpdaterRuntime,
} from '../services/desktopUpdater';
import {
  createDesktopUpdaterController,
  type DesktopUpdaterState,
} from '../services/desktopUpdaterController';

defineProps<{ collapsed: boolean }>();

const runtime = window as unknown as DesktopUpdaterRuntime;
const controller = createDesktopUpdaterController({
  supported: () => isWindowsDesktop(runtime),
  version: () => getCurrentDesktopVersion(runtime),
  check: () => checkForDesktopUpdate(runtime),
  install: (onProgress) => installDesktopUpdate(runtime, onProgress),
  errorMessage: desktopUpdateErrorMessage,
});
const state = shallowRef<DesktopUpdaterState>(controller.getState());
const modalVisible = ref(false);
let unsubscribe: (() => void) | undefined;

const currentVersion = computed(() => (
  'currentVersion' in state.value ? state.value.currentVersion : ''
));
const isBusy = computed(() => (
  state.value.phase === 'checking'
  || state.value.phase === 'downloading'
  || state.value.phase === 'installing'
));
const updateButtonLabel = computed(() => (
  state.value.phase === 'checking' ? '正在检查…' : '检查更新'
));
const modalTitle = computed(() => {
  if (state.value.phase === 'up_to_date') return '当前已是最新版本';
  if (state.value.phase === 'available') return '发现可用更新';
  if (state.value.phase === 'downloading') return '正在下载更新';
  if (state.value.phase === 'installing') return '正在安装更新';
  if (state.value.phase === 'error') return '更新未完成';
  return '桌面应用更新';
});
const modalDescription = computed(() => {
  if (state.value.phase === 'available') {
    return '安装前会自动完成签名校验，更新完成后重新启动桌面应用。';
  }
  if (state.value.phase === 'error') return '当前版本未被修改，可以重试或稍后再检查。';
  if (state.value.phase === 'up_to_date') return '暂时没有需要安装的新版本。';
  return '更新过程中请保持网络连接并不要关闭应用。';
});
const headerIconClass = computed(() => {
  if (state.value.phase === 'up_to_date') return 'bg-emerald-50 text-emerald-600';
  if (state.value.phase === 'error') return 'bg-rose-50 text-rose-600';
  return 'bg-blue-50 text-blue-600';
});
const formattedReleaseDate = computed(() => {
  if (state.value.phase !== 'available' || !state.value.manifest.date) return '';
  const parsed = new Date(state.value.manifest.date);
  return Number.isNaN(parsed.getTime())
    ? state.value.manifest.date
    : parsed.toLocaleDateString('zh-CN');
});
const formatBytes = (bytes: number) => {
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
};
const progressLabel = computed(() => {
  if (state.value.phase !== 'downloading') return '';
  if (state.value.percent !== null) return `${state.value.percent}%`;
  if (state.value.downloadedBytes > 0) return formatBytes(state.value.downloadedBytes);
  return '准备下载…';
});

const handleCheck = async () => {
  if (state.value.phase === 'available') {
    modalVisible.value = true;
    return;
  }
  await controller.check();
};
const handleInstall = async () => {
  await controller.install();
};
const handleRetry = async () => {
  await controller.retry();
};
const handleClose = () => {
  if (isBusy.value) return;
  modalVisible.value = false;
  controller.dismiss();
};

onMounted(async () => {
  unsubscribe = controller.subscribe((next) => {
    state.value = next;
    if (
      next.phase === 'up_to_date'
      || next.phase === 'available'
      || next.phase === 'downloading'
      || next.phase === 'installing'
      || next.phase === 'error'
    ) {
      modalVisible.value = true;
    }
  });
  await controller.initialize();
});

onUnmounted(() => unsubscribe?.());
</script>
