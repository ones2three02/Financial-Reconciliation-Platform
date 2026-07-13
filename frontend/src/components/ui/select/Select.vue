<script setup lang="ts">
import { ref, computed } from 'vue';
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

const selectedOption = computed(() => {
  return props.options.find(opt => opt.value === props.modelValue);
});

const selectOption = (val: any) => {
  if (props.disabled) return;
  emit('update:modelValue', val);
  emit('change', val);
  isOpen.value = false;
};
</script>

<template>
  <div class="relative inline-block text-left w-full">
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
    <div v-if="isOpen" class="fixed inset-0 z-40" @click="isOpen = false"></div>

    <!-- Dropdown Panel -->
    <transition name="popover-fade">
      <div
        v-if="isOpen"
        :class="
          cn(
            'absolute mt-1.5 w-full min-w-[150px] rounded-xl border border-slate-200 bg-white p-1.5 shadow-xl ring-1 ring-black/5 z-50 focus:outline-none max-h-[250px] overflow-y-auto',
            props.align === 'right' ? 'right-0 origin-top-right' : 'left-0 origin-top-left'
          )
        "
      >
        <button
          v-for="opt in props.options"
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
    </transition>
  </div>
</template>

<style scoped>
.popover-fade-enter-active,
.popover-fade-leave-active {
  transition: opacity 0.1s ease, transform 0.1;
}
.popover-fade-enter-from,
.popover-fade-leave-to {
  opacity: 0;
  transform: scale(0.97) translateY(-2px);
}
</style>
