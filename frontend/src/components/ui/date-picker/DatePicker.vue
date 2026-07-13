<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue';
import { Calendar as CalendarIcon, ChevronLeft, ChevronRight } from 'lucide-vue-next';
import { cn } from '../../../lib/utils';

const props = defineProps<{
  modelValue: string; // Format: YYYY-MM-DD
  class?: string;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', payload: string): void;
}>();

const isOpen = ref(false);

// Local calendar navigation states
const currentYear = ref(new Date().getFullYear());
const currentMonth = ref(new Date().getMonth()); // 0-indexed

// Sync calendar navigation view with external modelValue on mount and changes
const syncCalendarView = () => {
  if (props.modelValue) {
    const d = new Date(props.modelValue);
    if (!isNaN(d.getTime())) {
      currentYear.value = d.getFullYear();
      currentMonth.value = d.getMonth();
    }
  }
};

watch(() => props.modelValue, syncCalendarView);
onMounted(syncCalendarView);

const formattedDate = computed(() => {
  if (!props.modelValue) return '选择日期';
  const d = new Date(props.modelValue);
  if (isNaN(d.getTime())) return props.modelValue;
  return `${d.getFullYear()}年${String(d.getMonth() + 1).padStart(2, '0')}月${String(d.getDate()).padStart(2, '0')}日`;
});

const monthNames = ['一月', '二月', '三月', '四月', '五月', '六月', '七月', '八月', '九月', '十月', '十一月', '十二月'];

const daysInMonth = (year: number, month: number) => {
  return new Date(year, month + 1, 0).getDate();
};

const startWeekday = (year: number, month: number) => {
  return new Date(year, month, 1).getDay(); // 0 (Sun) to 6 (Sat)
};

const calendarDays = computed(() => {
  const days = [];
  const totalDays = daysInMonth(currentYear.value, currentMonth.value);
  const startDay = startWeekday(currentYear.value, currentMonth.value);

  // Previous month trailing days
  const prevMonth = currentMonth.value === 0 ? 11 : currentMonth.value - 1;
  const prevYear = currentMonth.value === 0 ? currentYear.value - 1 : currentYear.value;
  const totalPrevDays = daysInMonth(prevYear, prevMonth);

  for (let i = startDay - 1; i >= 0; i--) {
    const d = totalPrevDays - i;
    days.push({
      day: d,
      dateStr: `${prevYear}-${String(prevMonth + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`,
      isCurrentMonth: false
    });
  }

  // Current month days
  for (let i = 1; i <= totalDays; i++) {
    days.push({
      day: i,
      dateStr: `${currentYear.value}-${String(currentMonth.value + 1).padStart(2, '0')}-${String(i).padStart(2, '0')}`,
      isCurrentMonth: true
    });
  }

  // Next month leading days (to fill standard 42-day calendar block)
  const nextMonth = currentMonth.value === 11 ? 0 : currentMonth.value + 1;
  const nextYear = currentMonth.value === 11 ? currentYear.value + 1 : currentYear.value;
  let nextDay = 1;
  while (days.length < 42) {
    days.push({
      day: nextDay,
      dateStr: `${nextYear}-${String(nextMonth + 1).padStart(2, '0')}-${String(nextDay).padStart(2, '0')}`,
      isCurrentMonth: false
    });
    nextDay++;
  }

  return days;
});

const prevMonthView = () => {
  if (currentMonth.value === 0) {
    currentMonth.value = 11;
    currentYear.value--;
  } else {
    currentMonth.value--;
  }
};

const nextMonthView = () => {
  if (currentMonth.value === 11) {
    currentMonth.value = 0;
    currentYear.value++;
  } else {
    currentMonth.value++;
  }
};

const selectDay = (dateStr: string) => {
  emit('update:modelValue', dateStr);
  isOpen.value = false;
};
</script>

<template>
  <div class="relative inline-block text-left">
    <!-- Trigger Button -->
    <button
      type="button"
      @click="isOpen = !isOpen"
      :class="
        cn(
          'flex h-9 items-center justify-between gap-2.5 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 shadow-sm hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all select-none',
          props.class
        )
      "
    >
      <CalendarIcon class="h-4 w-4 text-slate-400 shrink-0" />
      <span class="tabular-nums font-bold">{{ formattedDate }}</span>
    </button>

    <!-- Transparent backdrop overlay for click-outside close -->
    <div v-if="isOpen" class="fixed inset-0 z-40" @click="isOpen = false"></div>

    <!-- Popover dropdown -->
    <transition name="popover-fade">
      <div
        v-if="isOpen"
        class="absolute right-0 mt-2 w-[270px] origin-top-right rounded-xl border border-slate-200 bg-white p-3.5 shadow-xl ring-1 ring-black/5 z-50 focus:outline-none"
      >
        <!-- Calendar Header -->
        <div class="flex items-center justify-between mb-3">
          <span class="text-xs font-extrabold text-slate-700 font-sans tracking-wide">
            {{ currentYear }}年 {{ monthNames[currentMonth] }}
          </span>
          <div class="flex items-center gap-1">
            <button
              type="button"
              @click="prevMonthView"
              class="p-1 rounded-lg hover:bg-slate-100 text-slate-500 hover:text-slate-800 transition-all"
            >
              <ChevronLeft class="h-4 w-4" />
            </button>
            <button
              type="button"
              @click="nextMonthView"
              class="p-1 rounded-lg hover:bg-slate-100 text-slate-500 hover:text-slate-800 transition-all"
            >
              <ChevronRight class="h-4 w-4" />
            </button>
          </div>
        </div>

        <!-- Calendar Month Weeks Header -->
        <div class="grid grid-cols-7 gap-1 text-center text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">
          <span>日</span>
          <span>一</span>
          <span>二</span>
          <span>三</span>
          <span>四</span>
          <span>五</span>
          <span>六</span>
        </div>

        <!-- Calendar Days Grid -->
        <div class="grid grid-cols-7 gap-1">
          <button
            v-for="cell in calendarDays"
            :key="cell.dateStr"
            type="button"
            @click="selectDay(cell.dateStr)"
            class="h-7 w-7 rounded-lg text-center text-xs font-semibold font-mono tabular-nums transition-all flex items-center justify-center"
            :class="[
              cell.dateStr === props.modelValue
                ? 'bg-blue-600 text-white font-extrabold shadow-sm shadow-blue-500/20'
                : cell.isCurrentMonth
                ? 'text-slate-700 hover:bg-slate-100'
                : 'text-slate-300 hover:bg-slate-50'
            ]"
          >
            {{ cell.day }}
          </button>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.popover-fade-enter-active,
.popover-fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.popover-fade-enter-from,
.popover-fade-leave-to {
  opacity: 0;
  transform: scale(0.96) translateY(-4px);
}
</style>
