<template>
  <Teleport to="body">
    <div class="fixed bottom-6 left-6 z-[9999] flex flex-col gap-3 max-w-sm w-80 pointer-events-none">
      <TransitionGroup 
        name="list" 
        tag="div" 
        class="flex flex-col gap-3 w-full"
      >
        <div
          v-for="item in activeAlerts"
          :key="item.id"
          class="pointer-events-auto bg-zinc-950/95 border border-zinc-800 text-zinc-300 rounded-xl p-4 shadow-2xl backdrop-blur-md flex flex-col gap-3 transition-all duration-300 relative"
        >
          <!-- Close Button -->
          <button 
            @click="dismiss(item.id)" 
            class="absolute top-3 right-3 text-zinc-500 hover:text-zinc-300 transition-colors p-0.5 rounded hover:bg-zinc-800"
          >
            <X class="w-3.5 h-3.5" />
          </button>

          <!-- Top Status and Filename -->
          <div class="flex items-start gap-3 pr-5">
            <div class="p-2 rounded-lg bg-zinc-900 text-zinc-400 border border-zinc-800 shrink-0">
              <Loader2 v-if="item.status === 'downloading'" class="w-4 h-4 animate-spin text-blue-500" />
              <FileCheck v-else-if="item.status === 'completed'" class="w-4 h-4 text-emerald-500" />
              <FileWarning v-else class="w-4 h-4 text-rose-500" />
            </div>
            
            <div class="min-w-0">
              <h4 class="font-bold text-xs text-zinc-100 truncate" :title="item.filename">
                {{ item.filename }}
              </h4>
              <p class="text-[10px] text-zinc-500 mt-0.5 font-medium">
                <span v-if="item.status === 'downloading'">正在保存文件...</span>
                <span v-else-if="item.status === 'completed'" class="text-emerald-500/90 font-semibold">保存成功</span>
                <span v-else class="text-rose-500/90 font-semibold">保存失败: {{ item.errorMessage || '未知错误' }}</span>
              </p>
            </div>
          </div>

          <!-- Bottom Action Buttons for completed downloads -->
          <div 
            v-if="item.status === 'completed'" 
            class="flex gap-2 border-t border-zinc-900/60 pt-2.5 mt-0.5"
          >
            <button
              @click="handleOpenFile(item.filePath)"
              class="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-[10px] font-bold transition-colors shadow-sm shadow-blue-500/10"
            >
              <ExternalLink class="w-3 h-3" />
              打开文件
            </button>
            <button
              @click="handleOpenFolder(item.filePath)"
              class="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 border border-zinc-800 rounded-lg text-[10px] font-bold transition-colors"
            >
              <FolderOpen class="w-3 h-3" />
              在访达中显示
            </button>
          </div>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue';
import { downloadHistory, openFile, openFolder } from '../services/download';
import { X, Loader2, FileCheck, FileWarning, FolderOpen, ExternalLink } from 'lucide-vue-next';

// Track which download items are currently visible in the notification toast
const visibleIds = ref<Record<string, boolean>>({});

// Keep track of timers to clear them up
const timers: Record<string, any> = {};

// Watch download history to trigger notifications
watch(
  () => downloadHistory.value,
  (newVal) => {
    newVal.forEach((item) => {
      // If we haven't tracked this item yet, show it
      if (visibleIds.value[item.id] === undefined) {
        visibleIds.value[item.id] = true;
      }
      
      // If download completes or fails, schedule auto-dismiss in 8 seconds
      if (item.status !== 'downloading') {
        if (timers[item.id]) {
          clearTimeout(timers[item.id]);
        }
        timers[item.id] = setTimeout(() => {
          dismiss(item.id);
        }, 8000);
      }
    });
  },
  { deep: true, immediate: true }
);

const activeAlerts = computed(() => {
  return downloadHistory.value.filter(item => visibleIds.value[item.id]);
});

const dismiss = (id: string) => {
  visibleIds.value[id] = false;
  if (timers[id]) {
    clearTimeout(timers[id]);
    delete timers[id];
  }
};

const handleOpenFile = (filePath: string) => {
  openFile(filePath);
};

const handleOpenFolder = (filePath: string) => {
  openFolder(filePath);
};
</script>

<style scoped>
.list-enter-active,
.list-leave-active {
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

.list-enter-from {
  opacity: 0;
  transform: translateY(20px) scale(0.95);
}

.list-leave-to {
  opacity: 0;
  transform: translateX(-40px) scale(0.95);
}

.list-move {
  transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}
</style>
