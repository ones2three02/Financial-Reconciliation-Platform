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

    <!-- Recent 7 Days Backlog Catch-up / Full Month Calendar Card -->
    <Card id="dashboard-trends-card" class="shadow-sm border border-slate-200/80">
      <CardHeader class="pb-2 flex flex-row items-center justify-between flex-wrap gap-4">
        <div>
          <CardTitle class="flex items-center gap-2.5 text-base font-bold text-slate-800">
            <CalendarDays class="w-4.5 h-4.5 text-blue-500 shrink-0" />
            <span>{{ viewMode === 'trends' ? '连续账期核验面板 (最近7天)' : '连续账期核验面板 (整月日历)' }}</span>
          </CardTitle>
          <CardDescription>
            {{ viewMode === 'trends' ? '查阅最近 7 天的每日对账覆盖状态，点击即可快速切换到对应账期进行核实对账' : '直观查看整月每天的对账结果与差异，随时补录历史数据' }}
          </CardDescription>
        </div>
        
        <!-- View Toggle Buttons -->
        <div class="flex items-center gap-1 bg-slate-100 p-1 rounded-xl shrink-0">
          <button 
            @click="viewMode = 'trends'"
            :class="[
              'px-3 py-1 text-[11px] font-bold rounded-lg transition-all',
              viewMode === 'trends' ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500 hover:text-slate-800'
            ]"
          >
            最近7天
          </button>
          <button 
            @click="viewMode = 'calendar'"
            :class="[
              'px-3 py-1 text-[11px] font-bold rounded-lg transition-all',
              viewMode === 'calendar' ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500 hover:text-slate-800'
            ]"
          >
            整月日历
          </button>
        </div>
      </CardHeader>
      
      <CardContent class="p-6 pt-2">
        <!-- 7-Day Trend Row View -->
        <div v-if="viewMode === 'trends'" class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-7 gap-4">
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

        <!-- Full Month Calendar View -->
        <div v-else class="space-y-4">
          <!-- Calendar Navigator -->
          <div class="flex items-center justify-between border-b border-slate-100 pb-3 shrink-0">
            <div class="flex items-center gap-2">
              <Button variant="outline" size="sm" class="h-8 w-8 p-0" @click="prevMonth">
                <ChevronLeft class="h-4 w-4 text-slate-600" />
              </Button>
              <span class="text-sm font-extrabold text-slate-800 tracking-wider font-mono">
                {{ calendarYear }} 年 {{ String(calendarMonth).padStart(2, '0') }} 月
              </span>
              <Button variant="outline" size="sm" class="h-8 w-8 p-0" @click="nextMonth">
                <ChevronRight class="h-4 w-4 text-slate-600" />
              </Button>
            </div>
            <div class="flex items-center gap-3">
              <!-- Indicators Legend -->
              <div class="hidden sm:flex items-center gap-4 text-[10px] font-bold text-slate-500 mr-2">
                <span class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-emerald-500"></span>全部一致</span>
                <span class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-rose-500"></span>有差异门店</span>
                <span class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-slate-300"></span>无比对数据</span>
              </div>
              <Button variant="outline" size="sm" class="h-8 text-xs font-bold" @click="goToToday">
                回到今天
              </Button>
            </div>
          </div>

          <!-- Weekday Labels -->
          <div class="grid grid-cols-7 gap-2 text-center text-[10px] font-bold uppercase tracking-wider text-slate-400 py-1">
            <div>一</div>
            <div>二</div>
            <div>三</div>
            <div>四</div>
            <div>五</div>
            <div class="text-slate-400/80">六</div>
            <div class="text-slate-400/80">日</div>
          </div>

          <!-- Calendar Grid (42 Cells) -->
          <div class="grid grid-cols-7 gap-2">
            <template v-for="week in calendarWeeks">
              <div 
                v-for="cell in week" 
                :key="cell.date"
                @click="goToDate(cell.date)"
                class="p-2 rounded-xl border flex flex-col justify-between h-[85px] cursor-pointer transition-all duration-150 relative bg-white select-none"
                :class="[
                  !cell.isCurrentMonth ? 'opacity-40 bg-slate-50/50 border-slate-100 hover:border-slate-200' : 'shadow-sm',
                  cell.isCurrentMonth && globalDate === cell.date 
                    ? 'border-blue-500 bg-blue-50/15 shadow-sm ring-1 ring-blue-500/25' 
                    : cell.isCurrentMonth ? 'border-slate-100 hover:border-slate-300 hover:shadow-md' : '',
                  isToday(cell.date) ? 'ring-2 ring-indigo-500/20' : ''
                ]"
              >
                <!-- Day Number & Today indicator -->
                <div class="flex items-center justify-between">
                  <span 
                    class="text-xs font-mono font-bold"
                    :class="[
                      globalDate === cell.date ? 'text-blue-600 font-extrabold' : 'text-slate-700',
                      isToday(cell.date) ? 'text-indigo-600 font-extrabold underline decoration-2' : ''
                    ]"
                  >
                    {{ cell.day }}
                  </span>
                  <span v-if="isToday(cell.date)" class="text-[8px] bg-indigo-50 text-indigo-600 px-1 rounded font-bold uppercase tracking-widest scale-90">今</span>
                </div>

                <!-- Status Badge -->
                <div class="mt-1">
                  <!-- Case 1: No data loaded yet -->
                  <div v-if="!calendarDataMap[cell.date]" class="text-[9px] text-slate-400 font-medium inline-flex items-center gap-1 scale-90 origin-left">
                    <span class="w-1.5 h-1.5 rounded-full bg-slate-200"></span>
                    <span>无数据</span>
                  </div>
                  <!-- Case 2: No stores / no data -->
                  <div v-else-if="calendarDataMap[cell.date].total_stores === 0" class="text-[9px] text-slate-400 font-medium inline-flex items-center gap-1 scale-90 origin-left">
                    <span class="w-1.5 h-1.5 rounded-full bg-slate-200"></span>
                    <span>无数据</span>
                  </div>
                  <!-- Case 3: Discrepancies present -->
                  <div v-else-if="calendarDataMap[cell.date].discrepancies > 0" class="text-[9px] text-rose-600 font-extrabold inline-flex items-center gap-1 bg-rose-50 px-1.5 py-0.5 rounded border border-rose-100 scale-90 origin-left">
                    <span class="w-1 h-1 rounded-full bg-rose-500 animate-pulse"></span>
                    <span>{{ calendarDataMap[cell.date].discrepancies }}家差异</span>
                  </div>
                  <!-- Case 4: Complete and Consistent -->
                  <div v-else class="text-[9px] text-emerald-600 font-bold inline-flex items-center gap-1 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-100 scale-90 origin-left">
                    <span class="w-1 h-1 rounded-full bg-emerald-500"></span>
                    <span>全部一致</span>
                  </div>
                </div>

                <!-- Hover action text / indicator -->
                <div class="text-[8px] text-slate-400 flex items-center justify-end font-semibold scale-90 origin-right select-none opacity-0 hover:opacity-100 transition-opacity">
                  {{ globalDate === cell.date ? '当前选中' : '点击切换' }}
                </div>
              </div>
            </template>
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
      <CardDescription>按日对比三方渠道收入合计与销售收入减现金</CardDescription>
        </CardHeader>
        <CardContent class="flex-1 w-full relative pt-2">
          <div ref="trendChartRef" class="w-full h-full"></div>
        </CardContent>
      </Card>

      <!-- Leaderboard / Discrepancy list -->
      <Card id="dashboard-discrepancy-stores" class="shadow-sm border border-slate-200/80 flex flex-col h-[400px]">
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
                <div class="font-bold text-slate-700 text-xs">
                  <div class="flex items-center gap-1.5 group/copy inline-flex">
                    <span class="select-text inline-block">{{ store.standard_store_name?.trim() }}</span>
                    <button 
                      @click="copyText(store.standard_store_name, store.id + '-dashboard-store')"
                      class="opacity-0 group-hover/copy:opacity-100 transition-opacity p-0.5 text-slate-400 hover:text-blue-600 rounded hover:bg-slate-100 shrink-0 flex items-center gap-1 scale-95"
                      title="点击复制"
                    >
                      <Check v-if="copiedId === store.id + '-dashboard-store'" class="w-3.5 h-3.5 text-emerald-500" />
                      <Copy v-else class="w-3.5 h-3.5" />
                      <span v-if="copiedId === store.id + '-dashboard-store'" class="text-[9px] text-emerald-500 font-bold">已复制</span>
                    </button>
                  </div>
                </div>
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
import { ref, onMounted, nextTick, watch, computed } from 'vue';
import { api } from '../services/api';
import type { DashboardSummary, ReconciliationResult, TrendData } from '../services/api';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Store as StoreIcon, CheckCircle2, AlertTriangle, Coins, LineChart, CalendarDays, ChevronLeft, ChevronRight, Copy, Check } from 'lucide-vue-next';
import { BarChart, LineChart as EChartsLineChart } from 'echarts/charts';
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components';
import { init, use, type EChartsType } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
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
const recentTrends = ref<TrendData[]>([]);

const copiedId = ref('');
const copyText = async (text: string, id: string) => {
  try {
    await navigator.clipboard.writeText(text);
    copiedId.value = id;
    setTimeout(() => {
      if (copiedId.value === id) {
        copiedId.value = '';
      }
    }, 1500);
  } catch (err) {
    console.error('Failed to copy text: ', err);
  }
};

const viewMode = ref<'trends' | 'calendar'>('trends');
const calendarYear = ref(new Date().getFullYear());
const calendarMonth = ref(new Date().getMonth() + 1);
const calendarDataMap = ref<Record<string, TrendData>>({});

const getLocalDateString = (d: Date) => {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const date = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${date}`;
};

const isToday = (dateStr: string) => {
  return getLocalDateString(new Date()) === dateStr;
};

const calendarWeeks = computed(() => {
  const year = calendarYear.value;
  const month = calendarMonth.value;
  const firstDay = new Date(year, month - 1, 1);
  const lastDay = new Date(year, month, 0);
  
  let startOffset = firstDay.getDay(); // 0 is Sunday
  startOffset = startOffset === 0 ? 6 : startOffset - 1; // Align Sunday to index 6, Monday to index 0
  
  const totalDays = lastDay.getDate();
  const prevLastDay = new Date(year, month - 1, 0).getDate();
  
  const cells = [];
  
  // Previous month padding
  for (let i = startOffset - 1; i >= 0; i--) {
    const dayNum = prevLastDay - i;
    const m = month - 1 === 0 ? 12 : month - 1;
    const y = month - 1 === 0 ? year - 1 : year;
    const dateStr = `${y}-${String(m).padStart(2, '0')}-${String(dayNum).padStart(2, '0')}`;
    cells.push({
      day: dayNum,
      date: dateStr,
      isCurrentMonth: false,
    });
  }
  
  // Current month days
  for (let i = 1; i <= totalDays; i++) {
    const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(i).padStart(2, '0')}`;
    cells.push({
      day: i,
      date: dateStr,
      isCurrentMonth: true,
    });
  }
  
  // Next month padding
  const remaining = 42 - cells.length;
  for (let i = 1; i <= remaining; i++) {
    const m = month + 1 === 13 ? 1 : month + 1;
    const y = month + 1 === 13 ? year + 1 : year;
    const dateStr = `${y}-${String(m).padStart(2, '0')}-${String(i).padStart(2, '0')}`;
    cells.push({
      day: i,
      date: dateStr,
      isCurrentMonth: false,
    });
  }
  
  const weeks = [];
  for (let i = 0; i < cells.length; i += 7) {
    weeks.push(cells.slice(i, i + 7));
  }
  return weeks;
});

const loadCalendarTrends = async () => {
  const weeks = calendarWeeks.value;
  if (!weeks.length) return;
  const startCellDate = weeks[0][0].date;
  const endCellDate = weeks[weeks.length - 1][6].date;
  
  try {
    const data = await api.getDashboardTrends({
      start_date: startCellDate,
      end_date: endCellDate
    });
    const map: Record<string, TrendData> = {};
    data.forEach(item => {
      map[item.date] = item;
    });
    calendarDataMap.value = map;
  } catch (error) {
    console.error('Failed to load calendar trends:', error);
  }
};

const nextMonth = () => {
  if (calendarMonth.value === 12) {
    calendarMonth.value = 1;
    calendarYear.value += 1;
  } else {
    calendarMonth.value += 1;
  }
};

const prevMonth = () => {
  if (calendarMonth.value === 1) {
    calendarMonth.value = 12;
    calendarYear.value -= 1;
  } else {
    calendarMonth.value -= 1;
  }
};

const goToToday = () => {
  const today = new Date();
  calendarYear.value = today.getFullYear();
  calendarMonth.value = today.getMonth() + 1;
  setGlobalDate(getLocalDateString(today));
};

// Sync calendar view month with globalDate when globalDate changes
watch(globalDate, (newDate) => {
  if (newDate) {
    const d = new Date(newDate);
    if (!isNaN(d.getTime())) {
      calendarYear.value = d.getFullYear();
      calendarMonth.value = d.getMonth() + 1;
    }
  }
});

// Watch calendar changes to trigger loadCalendarTrends
watch([calendarYear, calendarMonth], () => {
  if (viewMode.value === 'calendar') {
    void loadCalendarTrends();
  }
}, { immediate: true });

// Also watch viewMode to load if toggled
watch(viewMode, (newMode) => {
  if (newMode === 'calendar') {
    void loadCalendarTrends();
  }
});

use([BarChart, EChartsLineChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer]);

// Chart reference
const trendChartRef = ref<HTMLDivElement | null>(null);
let trendChart: EChartsType | null = null;

const initChart = (trends: TrendData[]) => {
  if (!trendChartRef.value) return;
  
  if (trendChart) {
    trendChart.dispose();
  }
  
  trendChart = init(trendChartRef.value);
  
  const dates = trends.map(t => t.date.slice(5)); // Show as MM-DD
  const sales = trends.map(t => t.sales_amount);
  const expected = trends.map(t => t.tonglian_amount);
  const diffs = trends.map(t => t.difference);
  
  const option = {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderWidth: 1,
      borderColor: '#e2e8f0',
      textStyle: { color: '#1e293b', fontSize: 11 },
      axisPointer: { type: 'shadow' }
    },
    legend: {
      data: ['销售减现金', '三方渠道合计', '两端差额'],
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
        name: '销售减现金',
        type: 'bar',
        barWidth: '15%',
        data: sales,
        itemStyle: {
          color: '#3b82f6',
          borderRadius: [3, 3, 0, 0]
        }
      },
      {
        name: '三方渠道合计',
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
    
    const trendData = await api.getDashboardTrends({ days: 7 });
    recentTrends.value = [...trendData].reverse(); // Copy and reverse to show newest first
    
    if (viewMode.value === 'calendar') {
      void loadCalendarTrends();
    }
    
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
