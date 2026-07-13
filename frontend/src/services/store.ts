import { ref, watch } from 'vue';

const getYesterdayStr = () => {
  const d = new Date();
  // By default, financial reconciliation is done for the previous day (yesterday)
  d.setDate(d.getDate() - 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};

// Global active trade date
export const globalDate = ref(localStorage.getItem('global-trade-date') || getYesterdayStr());

// Watch and persist changes
watch(globalDate, (newVal) => {
  if (newVal) {
    localStorage.setItem('global-trade-date', newVal);
  }
});

export const setGlobalDate = (dateStr: string) => {
  globalDate.value = dateStr;
};
