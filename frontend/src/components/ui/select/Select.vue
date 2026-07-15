<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue';
import { ChevronDown, Check } from 'lucide-vue-next';
import { cn } from '../../../lib/utils';

const props = withDefaults(
  defineProps<{
    modelValue: any;
    options: { value: any; label: string }[];
    placeholder?: string;
    class?: string;
    align?: 'left' | 'right';
    disabled?: boolean;
  }>(),
  {
    placeholder: '请选择',
    align: 'left',
    disabled: false
  }
);

const emit = defineEmits<{
  (e: 'update:modelValue', value: any): void;
  (e: 'change', value: any): void;
}>();

const isOpen = ref(false);
const triggerRef = ref<HTMLElement | null>(null);
const dropdownRef = ref<HTMLElement | null>(null);
const dropdownStyle = ref<Record<string, string>>({});
const searchQuery = ref('');

const filteredOptions = computed(() => {
  if (!searchQuery.value.trim()) return props.options;
  const q = searchQuery.value.toLowerCase().trim();
  return props.options.filter(opt => opt.label.toLowerCase().includes(q));
});

const selectedOption = computed(() => {
  return props.options.find(opt => opt.value === props.modelValue);
});

const selectOption = (val: any) => {
  if (props.disabled) return;
  emit('update:modelValue', val);
  emit('change', val);
  isOpen.value = false;
};

const updatePosition = () => {
  if (!triggerRef.value) return;
  const rect = triggerRef.value.getBoundingClientRect();

  // Calculate if it fits below or should be placed above
  const selectHeight = 250; // max-height is 250px
  const spaceBelow = window.innerHeight - rect.bottom;
  const placeAbove = spaceBelow < selectHeight && rect.top > selectHeight;

  dropdownStyle.value = {
    position: 'fixed',
    left: `${rect.left}px`,
    width: `${rect.width}px`,
    zIndex: '9999',
    ...(placeAbove
      ? { bottom: `${window.innerHeight - rect.top + 6}px` }
      : { top: `${rect.bottom + 6}px` }
    )
  };
};

const onScrollOrResize = (event: Event) => {
  if (event.type === 'scroll') {
    const target = event.target as HTMLElement;
    if (dropdownRef.value && (dropdownRef.value === target || dropdownRef.value.contains(target))) {
      return;
    }
  }
  isOpen.value = false;
};

watch(isOpen, (newVal) => {
  if (newVal) {
    searchQuery.value = '';
    updatePosition();
    window.addEventListener('scroll', onScrollOrResize, true);
    window.addEventListener('resize', onScrollOrResize);
  } else {
    window.removeEventListener('scroll', onScrollOrResize, true);
    window.removeEventListener('resize', onScrollOrResize);
  }
});

onUnmounted(() => {
  window.removeEventListener('scroll', onScrollOrResize, true);
  window.removeEventListener('resize', onScrollOrResize);
});
</script>

<template>
  <div ref="triggerRef" class="relative inline-block text-left w-full">
    <!-- Trigger Button -->
    <button
      type="button"
      @click="!props.disabled && (isOpen = !isOpen)"
      :disabled="props.disabled"
      :class="
        cn(
          'flex h-9 w-full items-center justify-between gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 shadow-sm transition-all focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-50 select-none text-left',
          props.class
        )
      "
    >
      <span class="truncate">
        {{ selectedOption ? selectedOption.label : props.placeholder }}
      </span>
      <ChevronDown class="h-4 w-4 text-slate-400 shrink-0 transition-transform duration-200" :class="{'rotate-180': isOpen}" />
    </button>

    <!-- Backdrop for click-outside close -->
    <Teleport to="body">
      <div v-if="isOpen" class="fixed inset-0 z-[9990]" @click="isOpen = false"></div>
    </Teleport>

    <!-- Dropdown Panel -->
    <Teleport to="body">
      <transition name="popover-fade">
        <div
          v-if="isOpen"
          ref="dropdownRef"
          :style="dropdownStyle"
          :class="
            cn(
              'border border-slate-200 bg-white p-1.5 shadow-xl ring-1 ring-black/5 focus:outline-none max-h-[280px] flex flex-col rounded-xl',
              props.align === 'right' ? 'origin-top-right' : 'origin-top-left'
            )
          "
        >
          <!-- Search Input -->
          <div v-if="options.length > 5" class="p-1 border-b border-slate-100 shrink-0">
            <input
              v-model="searchQuery"
              type="text"
              class="w-full rounded-lg border border-slate-100 bg-slate-50 px-2.5 py-1.5 text-xs outline-none focus:border-blue-500 focus:bg-white transition-all font-semibold"
              placeholder="搜索名称..."
              @click.stop
            />
          </div>

          <!-- Options List Container -->
          <div class="flex-1 overflow-y-auto min-h-0 py-1">
            <div v-if="filteredOptions.length === 0" class="px-3 py-4 text-center text-xs text-slate-400 font-medium">
              未找到匹配项
            </div>
            <button
              v-for="opt in filteredOptions"
              :key="String(opt.value)"
              type="button"
              @click="selectOption(opt.value)"
              class="flex w-full items-center justify-between rounded-lg px-2.5 py-2 text-left text-xs font-semibold transition-all hover:bg-slate-50"
              :class="[
                opt.value === props.modelValue
                  ? 'text-blue-600 bg-blue-50/20 font-extrabold'
                  : 'text-slate-700'
              ]"
            >
              <span class="truncate">{{ opt.label }}</span>
              <Check v-if="opt.value === props.modelValue" class="h-3.5 w-3.5 text-blue-600 shrink-0" />
            </button>
          </div>
        </div>
      </transition>
    </Teleport>
  </div>
</template>

<style scoped>
.popover-fade-enter-active,
.popover-fade-leave-active {
  transition: opacity 0.1s ease, transform 0.1s ease;
}
.popover-fade-enter-from,
.popover-fade-leave-to {
  opacity: 0;
  transform: scale(0.97) translateY(-2px);
}
</style>
