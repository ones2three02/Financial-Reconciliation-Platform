<template>
  <div class="space-y-8 fade-in">
    <!-- Top Filter Bar -->
    <Card class="shadow-sm border border-slate-200/80">
      <CardContent class="p-6 flex items-center justify-between flex-wrap gap-4">
        <div>
          <h3 class="text-base font-bold text-slate-800">对账数据监控大屏</h3>
          <p class="text-xs text-slate-400">实时查阅各门店今日收支比对、核对一致率以及偏差统计</p>
        </div>
        <div class="flex items-center gap-3">
          <label class="text-xs font-semibold text-slate-500 uppercase tracking-wider">选择账期日期:</label>
          <DatePicker v-model="globalDate" align="right" />
        </div>
      </CardContent>
    </Card>

    <!-- Quick Stats Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <!-- Card 1 -->
      <Card class="shadow-sm border border-slate-200/80 hover:shadow-md transition-shadow">
        <CardContent class="p-6 flex items-center gap-4">
          <div class="p-3 bg-blue-50 rounded-xl text-blue-600">
            <StoreIcon class="w-5 h-5" />
          </div>
          <div class="space-y-1">
            <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">对账门店总数</span>
            <div class="text-xl font-extrabold text-slate-800 leading-none">{{ summary.total_stores }} 家</div>
          </div>
        </CardContent>
      </Card>

      <!-- Card 2 -->
      <Card class="shadow-sm border border-slate-200/80 hover:shadow-md transition-shadow">
        <CardContent class="p-6 flex items-center gap-4">
          <div class="p-3 bg-emerald-50 rounded-xl text-emerald-600">
            <CheckCircle2 class="w-5 h-5" />
          </div>
          <div class="space-y-1">
            <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">账目一致率</span>
            <div class="text-xl font-extrabold text-emerald-600 leading-none">
              {{ summary.total_stores ? Math.round((summary.consistent_count / summary.total_stores) * 100) : 0 }}%
            </div>
            <span class="text-[9px] text-slate-400 font-medium block">正常门店: {{ summary.consistent_count }} 家</span>
          </div>
        </CardContent>
      </Card>

      <!-- Card 3 -->
      <Card class="shadow-sm border border-slate-200/80 hover:shadow-md transition-shadow">
        <CardContent class="p-6 flex items-center gap-4">
          <div class="p-3 bg-rose-50 rounded-xl text-rose-600">
            <AlertTriangle class="w-5 h-5" />
          </div>
          <div class="space-y-1">
            <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">异常/缺失门店</span>
            <div class="text-xl font-extrabold text-rose-600 leading-none">
              {{ summary.discrepancy_count + summary.missing_data_count }} 家
            </div>
            <span class="text-[9px] text-slate-400 font-medium block">金额不符: {{ summary.discrepancy_count }} | 缺失: {{ summary.missing_data_count }}</span>
          </div>
        </CardContent>
      </Card>

      <!-- Card 4 -->
      <Card class="shadow-sm border border-slate-200/80 hover:shadow-md transition-shadow">
        <CardContent class="p-6 flex items-center gap-4">
          <div class="p-3 bg-amber-50 rounded-xl text-amber-600">
            <Coins class="w-5 h-5" />
          </div>
          <div class="space-y-1">
            <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">今日偏差金额</span>
            <div class="text-xl font-extrabold text-slate-800 leading-none">
              ¥{{ Number(summary.total_difference).toLocaleString('zh-CN', { minimumFractionDigits: 2 }) }}
            </div>
            <span class="text-[9px] text-slate-400 font-medium block">所有异常门店差异绝对值汇总</span>
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- Recent 7 Days Backlog Catch-up Card -->
    <Card class="shadow-sm border border-slate-200/80">
      <CardHeader class="pb-2">
        <CardTitle class="flex items-center gap-2.5 text-base font-bold text-slate-800">
          <CalendarDays class="w-4.5 h-4.5 text-blue-500" />
          <span>连续账期核验面板 (支持假期归来补账)</span>
        </CardTitle>
        <CardDescription>查阅最近 7 天的每日对账覆盖状态，点击即可快速切换到对应账期进行核实对账</CardDescription>
      </CardHeader>
      <CardContent class="p-6 pt-2">
        <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-7 gap-4">
          <div 
            v-for="day in recentTrends" 
            :key="day.date"
            class="p-4 rounded-xl border flex flex-col justify-between h-[125px] transition-all duration-150 bg-white"
            :class="
              globalDate === day.date 
                ? 'border-blue-500 bg-blue-50/10 shadow-sm ring-1 ring-blue-500/20' 
                : 'border-slate-100 hover:border-slate-200 shadow-sm hover:shadow-md'
            "
          >
            <div>
              <div class="text-[10px] font-bold text-slate-400 font-mono tracking-wider">{{ day.date.slice(5) }} ({{ getDayOfWeek(day.date) }})</div>
              
              <!-- Status text with badges -->
              <div class="mt-2.5 text-xs font-extrabold">
                <span v-if="day.total_stores === 0" class="text-slate-400 inline-flex items-center gap-1">
                  <span class="w-1.5 h-1.5 rounded-full bg-slate-300"></span>
                  <span>无比对数据</span>
                </span>
                <span v-else-if="day.discrepancies > 0" class="text-rose-600 inline-flex items-center gap-1">
                  <span class="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse"></span>
                  <span>{{ day.discrepancies }} 家差异</span>
                </span>
                <span v-else class="text-emerald-600 inline-flex items-center gap-1">
                  <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                  <span>全部一致</span>
                </span>
              </div>
            </div>

            <!-- Action button -->
            <Button 
              @click="goToDate(day.date)"
              variant="ghost"
              size="xs"
              class="w-full text-[10px] font-bold h-7 border rounded-lg transition-all"
              :class="
                day.date === globalDate 
                  ? 'bg-blue-600 text-white border-blue-600 hover:bg-blue-700' 
                  : 'text-slate-600 hover:text-blue-600 hover:bg-slate-50 border-slate-200/60'
              "
            >
              <span>{{ day.date === globalDate ? '当前账期' : '切换核验' }}</span>
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>

    <!-- Charts and Leaders Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <!-- Trend Line Chart -->
      <Card class="lg:col-span-2 shadow-sm border border-slate-200/80 flex flex-col h-[400px]">
        <CardHeader class="pb-2">
          <CardTitle class="flex items-center gap-2 text-sm font-bold text-slate-800">
            <LineChart class="w-4 h-4 text-blue-500" />
            <span>近 7 天收支趋势比对</span>
          </CardTitle>
          <CardDescription>按日对比门店总应收(Expected)与后台实收(Actual)</CardDescription>
        </CardHeader>
        <CardContent class="flex-1 w-full relative pt-2">
          <div ref="trendChartRef" class="w-full h-full"></div>
        </CardContent>
      </Card>

      <!-- Leaderboard / Discrepancy list -->
      <Card class="shadow-sm border border-slate-200/80 flex flex-col h-[400px]">
        <CardHeader class="pb-2">
          <CardTitle class="flex items-center gap-2 text-sm font-bold text-slate-800">
            <AlertTriangle class="w-4 h-4 text-rose-500" />
            <span>当前差异排行 (Top 5)</span>
          </CardTitle>
          <CardDescription>差额绝对值越大，代表对账异常越严重</CardDescription>
        </CardHeader>
        <CardContent class="flex-1 overflow-y-auto space-y-3 pt-2">
          <div v-if="discrepancyStores.length === 0" class="h-full flex flex-col items-center justify-center text-slate-400 gap-2">
            <CheckCircle2 class="w-8 h-8 text-emerald-500" />
            <span class="text-xs font-semibold">当前暂无对账异常门店</span>
          </div>
          <div 
            v-for="(store, index) in discrepancyStores.slice(0, 5)" 
            :key="store.id"
            class="flex items-center justify-between p-3.5 bg-slate-50/50 hover:bg-slate-50 border border-slate-100 rounded-xl transition-all duration-150"
          >
            <div class="flex items-center gap-3">
              <span class="w-5 h-5 rounded-full bg-slate-200 text-[10px] font-bold text-slate-600 flex items-center justify-center">
                {{ index + 1 }}
              </span>
              <div>
                <div class="font-bold text-slate-700 text-xs">{{ store.standard_store_name }}</div>
                <div class="text-[9px] text-slate-400 font-semibold uppercase tracking-wider">
                  {{ store.status === 'missing_data' ? '缺少渠道数据' : '账面存在差异' }}
                </div>
              </div>
            </div>
            <div class="text-right">
              <div class="font-extrabold text-rose-600 text-xs">
                ¥{{ Math.abs(store.difference).toLocaleString('zh-CN', { minimumFractionDigits: 2 }) }}
              </div>
              <router-link to="/reconciliation" class="text-[9px] text-blue-600 font-bold hover:underline">
                去核实 →
              </router-link>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, watch } from 'vue';
import { api } from '../services/api';
import type { DashboardSummary, ReconciliationResult } from '../services/api';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Store as StoreIcon, CheckCircle2, AlertTriangle, Coins, LineChart, CalendarDays } from 'lucide-vue-next';
import * as echarts from 'echarts';
import { globalDate, setGlobalDate } from '../services/store';
import { DatePicker } from '../components/ui/date-picker';

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
const recentTrends = ref<any[]>([]);

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
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderWidth: 1,
      borderColor: '#e2e8f0',
      textStyle: { color: '#1e293b', fontSize: 11 },
      axisPointer: { type: 'shadow' }
    },
    legend: {
      data: ['预期销售 (应收)', '三方后台 (实收)', '两端差额'],
      bottom: 0,
      itemWidth: 10,
      itemHeight: 10,
      textStyle: { color: '#64748b', fontSize: 11 }
    },
    grid: {
      top: '10%',
      left: '3%',
      right: '4%',
      bottom: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisLabel: { color: '#64748b', fontSize: 10 }
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      splitLine: { lineStyle: { color: '#f1f5f9' } },
      axisLabel: { color: '#64748b', fontSize: 10 }
    },
    series: [
      {
        name: '预期销售 (应收)',
        type: 'bar',
        barWidth: '15%',
        data: sales,
        itemStyle: {
          color: '#3b82f6',
          borderRadius: [3, 3, 0, 0]
        }
      },
      {
        name: '三方后台 (实收)',
        type: 'bar',
        barWidth: '15%',
        data: expected,
        itemStyle: {
          color: '#10b981',
          borderRadius: [3, 3, 0, 0]
        }
      },
      {
        name: '两端差额',
        type: 'line',
        data: diffs,
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        itemStyle: { color: '#ef4444' },
        lineStyle: { width: 2, type: 'dashed' }
      }
    ]
  };
  
  trendChart.setOption(option);
};

const getDayOfWeek = (dateStr: string) => {
  const days = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
  const d = new Date(dateStr);
  return days[d.getDay()];
};

const goToDate = (dateStr: string) => {
  setGlobalDate(dateStr);
};

const fetchDashboardData = async () => {
  try {
    const sumData = await api.getDashboardSummary(globalDate.value);
    summary.value = sumData;
    
    const reconData = await api.getReconciliationResults({
      trade_date: globalDate.value,
      is_resolved: false
    });
    discrepancyStores.value = reconData.filter(r => r.status !== 'consistent');
    
    const trendData = await api.getDashboardTrends(7);
    recentTrends.value = [...trendData].reverse(); // Copy and reverse to show newest first
    
    nextTick(() => {
      initChart(trendData);
    });
  } catch (error) {
    console.error('Failed to load dashboard data:', error);
  }
};

const handleResize = () => {
  if (trendChart) {
    trendChart.resize();
  }
};

watch(globalDate, () => {
  fetchDashboardData();
});

onMounted(() => {
  fetchDashboardData();
  window.addEventListener('resize', handleResize);
});
</script>
