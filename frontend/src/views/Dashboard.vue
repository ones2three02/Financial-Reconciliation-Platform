<template>
  <div class="space-y-8 fade-in">
    <!-- Top Filter Bar -->
    <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 flex items-center justify-between flex-wrap gap-4">
      <div>
        <h3 class="text-xl font-bold text-slate-900">数据大屏</h3>
        <p class="text-slate-500 text-sm">今日整体对账概览与收支平衡趋势分析</p>
      </div>
      <div class="flex items-center gap-3">
        <label for="date-select" class="text-sm font-medium text-slate-600">选择对账日期:</label>
        <input 
          id="date-select"
          type="date" 
          v-model="selectedDate" 
          @change="fetchDashboardData"
          class="border border-slate-200 rounded-xl px-4 py-2 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>
    </div>

    <!-- Quick Stats Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <!-- Card 1 -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 flex items-center gap-5 dashboard-card">
        <div class="p-4 bg-blue-50 rounded-xl text-blue-600 text-2xl">🏪</div>
        <div class="space-y-1">
          <div class="text-xs font-semibold text-slate-400 uppercase tracking-wider">对账门店数</div>
          <div class="text-2xl font-bold text-slate-800">{{ summary.total_stores }}</div>
          <div class="text-xs text-slate-500">今日参与对账门店</div>
        </div>
      </div>

      <!-- Card 2 -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 flex items-center gap-5 dashboard-card">
        <div class="p-4 bg-emerald-50 rounded-xl text-emerald-600 text-2xl">✅</div>
        <div class="space-y-1">
          <div class="text-xs font-semibold text-slate-400 uppercase tracking-wider">账目一致门店</div>
          <div class="text-2xl font-bold text-emerald-600">{{ summary.consistent_count }}</div>
          <div class="text-xs text-slate-500">
            占比: {{ summary.total_stores ? Math.round((summary.consistent_count / summary.total_stores) * 100) : 0 }}%
          </div>
        </div>
      </div>

      <!-- Card 3 -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 flex items-center gap-5 dashboard-card">
        <div class="p-4 bg-rose-50 rounded-xl text-rose-600 text-2xl">⚠️</div>
        <div class="space-y-1">
          <div class="text-xs font-semibold text-slate-400 uppercase tracking-wider">异常/差异门店</div>
          <div class="text-2xl font-bold text-rose-600">{{ summary.discrepancy_count }}</div>
          <div class="text-xs text-slate-500">缺少数据: {{ summary.missing_data_count }}</div>
        </div>
      </div>

      <!-- Card 4 -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 flex items-center gap-5 dashboard-card">
        <div class="p-4 bg-amber-50 rounded-xl text-amber-600 text-2xl">💰</div>
        <div class="space-y-1">
          <div class="text-xs font-semibold text-slate-400 uppercase tracking-wider">差异总金额</div>
          <div class="text-2xl font-bold text-slate-800">
            ¥{{ Number(summary.total_difference).toLocaleString('zh-CN', { minimumFractionDigits: 2 }) }}
          </div>
          <div class="text-xs text-slate-500">所有异常门店差异额汇总</div>
        </div>
      </div>
    </div>

    <!-- Charts and Leaders Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <!-- Trend Line Chart -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 lg:col-span-2 flex flex-col h-[400px]">
        <div class="flex justify-between items-center mb-6">
          <div>
            <h4 class="font-bold text-slate-800">近7天对账趋势</h4>
            <p class="text-xs text-slate-500">对比每日总应收(Expected)与实收(Actual)</p>
          </div>
          <div class="text-xs text-slate-400">单位: 元</div>
        </div>
        <div ref="trendChartRef" class="flex-1 w-full"></div>
      </div>

      <!-- Leaderboard / Discrepancy list -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 flex flex-col h-[400px]">
        <div class="mb-4">
          <h4 class="font-bold text-slate-800">今日差异排行 (Top 5)</h4>
          <p class="text-xs text-slate-500">差额数值越大，代表异常越严重</p>
        </div>
        <div class="flex-1 overflow-y-auto pr-1 space-y-3">
          <div v-if="discrepancyStores.length === 0" class="h-full flex flex-col items-center justify-center text-slate-400 text-sm gap-2">
            <span>🎉</span>
            <span>今日暂无异常门店</span>
          </div>
          <div 
            v-for="(store, index) in discrepancyStores.slice(0, 5)" 
            :key="store.id"
            class="flex items-center justify-between p-3.5 bg-slate-50 hover:bg-slate-100/80 rounded-xl transition-all duration-200 border border-slate-100"
          >
            <div class="flex items-center gap-3">
              <span class="w-6 h-6 rounded-full bg-slate-200 text-xs font-bold text-slate-600 flex items-center justify-center">
                {{ index + 1 }}
              </span>
              <div>
                <div class="font-semibold text-slate-800 text-sm">{{ store.standard_store_name }}</div>
                <div class="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">
                  {{ store.status === 'missing_data' ? '缺少来源数据' : '金额不匹配' }}
                </div>
              </div>
            </div>
            <div class="text-right">
              <div class="font-bold text-rose-600 text-sm">
                ¥{{ Math.abs(store.difference).toLocaleString('zh-CN', { minimumFractionDigits: 2 }) }}
              </div>
              <router-link to="/reconciliation" class="text-[10px] text-blue-600 font-medium hover:underline">
                查看明细 →
              </router-link>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue';
import { api } from '../services/api';
import type { DashboardSummary, ReconciliationResult } from '../services/api';
import * as echarts from 'echarts';

// Date state (defaults to today)
const getTodayStr = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};

const selectedDate = ref(getTodayStr());

const summary = ref<DashboardSummary>({
  total_stores: 0,
  consistent_count: 0,
  discrepancy_count: 0,
  missing_data_count: 0,
  total_sales: 0,
  total_tonglian: 0,
  total_difference: 0
});

const discrepancyStores = ref<ReconciliationResult[]>([]);

// Chart reference
const trendChartRef = ref<HTMLDivElement | null>(null);
let trendChart: echarts.ECharts | null = null;

const initChart = (trends: any[]) => {
  if (!trendChartRef.value) return;
  
  if (trendChart) {
    trendChart.dispose();
  }
  
  trendChart = echarts.init(trendChartRef.value);
  
  const dates = trends.map(t => t.date.slice(5)); // Show as MM-DD
  const sales = trends.map(t => t.sales_amount);
  const expected = trends.map(t => t.tonglian_amount);
  const diffs = trends.map(t => t.difference);
  
  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#1e293b',
      borderWidth: 0,
      textStyle: { color: '#f8fafc' },
      axisPointer: { type: 'shadow' }
    },
    legend: {
      data: ['实际销售', '后台收入', '应收实收差额'],
      bottom: 0,
      textStyle: { color: '#64748b' }
    },
    grid: {
      top: '10%',
      left: '3%',
      right: '4%',
      bottom: '12%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisLabel: { color: '#64748b' }
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      splitLine: { lineStyle: { color: '#f1f5f9' } },
      axisLabel: { color: '#64748b' }
    },
    series: [
      {
        name: '实际销售',
        type: 'bar',
        barWidth: '20%',
        data: sales,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#3b82f6' },
            { offset: 1, color: '#1d4ed8' }
          ]),
          borderRadius: [4, 4, 0, 0]
        }
      },
      {
        name: '后台收入',
        type: 'bar',
        barWidth: '20%',
        data: expected,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#34d399' },
            { offset: 1, color: '#059669' }
          ]),
          borderRadius: [4, 4, 0, 0]
        }
      },
      {
        name: '应收实收差额',
        type: 'line',
        data: diffs,
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        itemStyle: { color: '#f43f5e' },
        lineStyle: { width: 2.5, type: 'dashed' }
      }
    ]
  };
  
  trendChart.setOption(option);
};

const fetchDashboardData = async () => {
  try {
    // 1. Fetch dashboard summary
    const sumData = await api.getDashboardSummary(selectedDate.value);
    summary.value = sumData;
    
    // 2. Fetch discrepancy leaderboard
    const reconData = await api.getReconciliationResults({
      trade_date: selectedDate.value,
      is_resolved: false
    });
    discrepancyStores.value = reconData.filter(r => r.status !== 'consistent');
    
    // 3. Fetch trends
    const trendData = await api.getDashboardTrends(7);
    nextTick(() => {
      initChart(trendData);
    });
  } catch (error) {
    console.error('Failed to load dashboard data:', error);
  }
};

// Window resize listener
const handleResize = () => {
  if (trendChart) {
    trendChart.resize();
  }
};

onMounted(() => {
  fetchDashboardData();
  window.addEventListener('resize', handleResize);
});
</script>
