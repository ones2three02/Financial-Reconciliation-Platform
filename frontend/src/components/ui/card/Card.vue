<script setup lang="ts">
import { cn } from '../../../lib/utils';

const props = defineProps<{
  class?: string;
}>();
</script>

<template>
  <div
    :class="
      cn(
        'rounded-2xl border border-slate-200/80 bg-card text-card-foreground shadow-sm transition-all duration-200',
        props.class,
      )
    "
  >
    <slot />
  </div>
</template>
