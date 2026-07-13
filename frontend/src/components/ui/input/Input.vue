<script setup lang="ts">
import { cn } from '../../../lib/utils';

const props = defineProps<{
  modelValue?: string | number;
  class?: string;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', payload: string | number): void;
}>();
</script>

<template>
  <input
    :value="modelValue"
    @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
    :class="
      cn(
        'flex h-10 w-full rounded-xl border border-slate-200 bg-background px-4 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-slate-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 transition-all',
        props.class,
      )
    "
  />
</template>
