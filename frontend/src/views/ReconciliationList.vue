<template>
  <div class="space-y-8 fade-in">
    <!-- Filter & Action Bar Card -->
    <Card class="shadow-sm border border-slate-200/80">
      <CardContent class="p-6 flex flex-wrap items-center justify-between gap-6">
        <div class="flex flex-wrap items-center gap-5">
          <!-- Date Filter -->
          <div class="flex flex-col gap-1.5">
            <label class="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1">
              <Calendar class="w-3.5 h-3.5" />
              <span>账期日期</span>
            </label>
            <DatePicker v-model="globalDate" />
          </div>

          <!-- Status Filter -->
          <div class="flex flex-col gap-1.5">
            <label for="filter-status" class="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1">
              <Sliders class="w-3.5 h-3.5" />
              <span>比对状态</span>
            </label>
            <select 
              id="filter-status"
              v-model="filterStatus" 
              @change="fetchResults"
              class="border border-slate-200 rounded-lg px-3 py-1.5 text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white h-9 min-w-[120px] select-custom"
            >
              <option value="">全部</option>
              <option value="consistent">账目一致</option>
              <option value="discrepancy">有差异</option>
              <option value="missing_data">缺少数据</option>
            </select>
          </div>

          <!-- Resolution Filter -->
          <div class="flex flex-col gap-1.5">
            <label for="filter-resolved" class="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1">
              <CheckCircle2 class="w-3.5 h-3.5" />
              <span>核实处理</span>
            </label>
            <select 
              id="filter-resolved"
              v-model="filterResolved" 
              @change="fetchResults"
              class="border border-slate-200 rounded-lg px-3 py-1.5 text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white h-9 min-w-[100px] select-custom"
            >
              <option value="">全部</option>
              <option value="false">未处理</option>
              <option value="true">已处理</option>
            </select>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="flex items-center gap-3.5 shrink-0 self-end">
          <Button 
            @click="recalculate"
            variant="outline"
            size="sm"
            class="h-9 font-semibold text-xs border border-slate-200/80 hover:bg-slate-50 flex items-center gap-1.5"
            :disabled="isRecalculating"
          >
            <RefreshCw class="w-3.5 h-3.5" :class="{'animate-spin': isRecalculating}" />
            <span>重新对账</span>
          </Button>
          
          <Button 
            @click="exportExcel"
            size="sm"
            class="h-9 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs shadow-md shadow-emerald-500/10 flex items-center gap-1.5"
          >
            <Download class="w-3.5 h-3.5" />
            <span>导出报表</span>
          </Button>
        </div>
      </CardContent>
    </Card>

    <!-- Main Results Card / Table -->
    <Card class="shadow-sm border border-slate-200/80 overflow-hidden">
      <CardContent class="p-0">
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-50 text-slate-400 text-[10px] font-bold uppercase tracking-wider border-b border-slate-200/80">
                <th class="p-4">标准门店</th>
                <th class="p-4 text-right">销售系统 (S)</th>
                <th class="p-4 text-right">交班现金 (C)</th>
                <th class="p-4 text-right">计算应收 (S - C)</th>
                <th class="p-4 text-right">后台实收汇总 (P)</th>
                <th class="p-4 text-right">偏差额 (P - 应收)</th>
                <th class="p-4 text-center">状态</th>
                <th class="p-4">核实备注</th>
                <th class="p-4 text-center">操作</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-xs">
              <tr v-if="results.length === 0">
                <td colspan="9" class="p-12 text-center text-slate-400 font-medium">
                  <div class="flex flex-col items-center justify-center gap-2">
                    <FolderOpen class="w-8 h-8 text-slate-300" />
                    <span>该账期无对账明细，请确认是否导入相应流水文件</span>
                  </div>
                </td>
              </tr>
              <tr 
                v-for="r in results" 
                :key="r.id"
                class="hover:bg-slate-50/40 transition-colors"
                :class="{'bg-rose-50/5': r.status === 'discrepancy' && !r.is_resolved}"
              >
                <td class="p-4 font-bold text-slate-700">{{ r.standard_store_name }}</td>
                <td class="p-4 text-right font-semibold text-slate-600">¥{{ Number(r.sales_amount).toLocaleString('zh-CN', {minimumFractionDigits: 2}) }}</td>
                <td class="p-4 text-right font-semibold text-slate-600">¥{{ Number(r.cash_amount).toLocaleString('zh-CN', {minimumFractionDigits: 2}) }}</td>
                <td class="p-4 text-right font-bold text-slate-700 bg-slate-50/30">
                  ¥{{ Number(r.actual_amount).toLocaleString('zh-CN', {minimumFractionDigits: 2}) }}
                </td>
                <td class="p-4 text-right font-bold text-slate-700" title="通联+美团+抖音">
                  ¥{{ Number(r.expected_amount).toLocaleString('zh-CN', {minimumFractionDigits: 2}) }}
                </td>
                <td class="p-4 text-right font-extrabold" :class="getDifferenceClass(r)">
                  {{ getDifferencePrefix(r.difference) }}¥{{ Math.abs(r.difference).toLocaleString('zh-CN', {minimumFractionDigits: 2}) }}
                </td>
                <td class="p-4 text-center">
                  <span 
                    class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold"
                    :class="getStatusBadgeClass(r.status)"
                  >
                    <span class="w-1.5 h-1.5 rounded-full" :class="getStatusDotClass(r.status)"></span>
                    <span>{{ getStatusLabel(r.status) }}</span>
                  </span>
                </td>
                <td class="p-4 max-w-xs truncate text-slate-400 font-medium" :title="r.remarks || ''">
                  {{ r.remarks || '—' }}
                </td>
                <td class="p-4 text-center">
                  <Button 
                    @click="openAuditModal(r)"
                    variant="ghost"
                    size="xs"
                    class="h-7 border border-slate-200 hover:bg-slate-50 text-[11px] font-bold text-slate-700"
                  >
                    📝 核实
                  </Button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>

    <!-- Audit Dialog Modal (shadcn style) -->
    <div 
      v-if="showAuditModal" 
      class="fixed inset-0 bg-zinc-950/40 backdrop-blur-sm z-50 flex items-center justify-center p-4 fade-in"
      @click.self="showAuditModal = false"
    >
      <Card class="w-full max-w-md shadow-2xl border border-slate-200/80 overflow-hidden bg-white">
        <CardHeader class="bg-slate-50/50 border-b border-slate-200/60 pb-4">
          <div class="flex items-center justify-between">
            <div>
              <CardTitle class="text-base font-bold text-slate-800">门店对账核实</CardTitle>
              <CardDescription class="text-xs text-slate-400">标准门店: {{ activeRow?.standard_store_name }} ({{ activeRow?.trade_date }})</CardDescription>
            </div>
            <button @click="showAuditModal = false" class="text-slate-400 hover:text-slate-600 text-lg font-bold">×</button>
          </div>
        </CardHeader>
        
        <CardContent class="p-6 space-y-5">
          <!-- Summary Metrics inside modal -->
          <div class="grid grid-cols-2 gap-4 p-4 bg-slate-50 border border-slate-200/60 rounded-xl text-xs font-semibold">
            <div>
              <span class="text-slate-400 block mb-0.5">计算应收 (销售-现金)</span>
              <span class="font-bold text-slate-700 text-sm">¥{{ activeRow ? Number(activeRow.actual_amount).toLocaleString('zh-CN', {minimumFractionDigits: 2}) : '0.00' }}</span>
            </div>
            <div>
              <span class="text-slate-400 block mb-0.5">三方实收汇总</span>
              <span class="font-bold text-slate-700 text-sm">¥{{ activeRow ? Number(activeRow.expected_amount).toLocaleString('zh-CN', {minimumFractionDigits: 2}) : '0.00' }}</span>
            </div>
            <div class="col-span-2 border-t border-slate-200/80 pt-2.5 flex items-center justify-between">
              <span class="text-slate-500">偏差金额</span>
              <span class="font-bold text-sm" :class="activeRow ? getDifferenceClass(activeRow) : ''">
                ¥{{ activeRow ? Number(activeRow.difference).toLocaleString('zh-CN', {minimumFractionDigits: 2}) : '0.00' }}
              </span>
            </div>
          </div>

          <!-- Inputs -->
          <div class="space-y-4">
            <div class="flex flex-col gap-1.5">
              <label for="audit-remark" class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">异常成因备注</label>
              <textarea 
                id="audit-remark"
                v-model="auditRemark" 
                rows="3" 
                placeholder="例如: 财务确认今日美团因退款延迟核销导致100元差异，已与店长核实。"
                class="border border-slate-200 rounded-xl px-3.5 py-2.5 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              ></textarea>
            </div>

            <div class="flex items-center gap-2">
              <input 
                id="is-resolved-cb"
                type="checkbox" 
                v-model="auditResolved" 
                class="rounded border-slate-300 text-blue-600 focus:ring-blue-500 w-4 h-4"
              />
              <label for="is-resolved-cb" class="text-xs font-bold text-slate-700 cursor-pointer">
                已核实并标记解决 (Resolved)
              </label>
            </div>
          </div>
        </CardContent>

        <CardFooter class="bg-slate-50/50 border-t border-slate-200/60 p-4 flex justify-end gap-3">
          <Button 
            @click="showAuditModal = false"
            variant="outline"
            size="sm"
            class="h-8 text-xs font-semibold"
          >
            取消
          </Button>
          <Button 
            @click="saveAudit"
            size="sm"
            class="h-8 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs shadow-md shadow-blue-500/10"
          >
            保存备注
          </Button>
        </CardFooter>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import { api } from '../services/api';
import type { ReconciliationResult } from '../services/api';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Calendar, Sliders, CheckCircle2, RefreshCw, Download, FolderOpen } from 'lucide-vue-next';
import { globalDate } from '../services/store';
import { DatePicker } from '../components/ui/date-picker';

// Filter states
const filterStatus = ref('');
const filterResolved = ref('');

const results = ref<ReconciliationResult[]>([]);
const isRecalculating = ref(false);

// Audit Modal states
const showAuditModal = ref(false);
const activeRow = ref<ReconciliationResult | null>(null);
const auditRemark = ref('');
const auditResolved = ref(false);

const getDifferenceClass = (row: ReconciliationResult) => {
  if (row.status === 'consistent') return 'text-emerald-600';
  return row.difference > 0 ? 'text-blue-600' : 'text-rose-600';
};

const getDifferencePrefix = (diff: number) => {
  if (diff > 0) return '+';
  return '';
};

const getStatusBadgeClass = (status: string) => {
  switch (status) {
    case 'consistent': return 'bg-emerald-50 text-emerald-600 border border-emerald-150';
    case 'discrepancy': return 'bg-rose-50 text-rose-600 border border-rose-150';
    case 'missing_data': return 'bg-amber-50 text-amber-600 border border-amber-150';
    default: return 'bg-slate-100 text-slate-600 border border-slate-200';
  }
};

const getStatusDotClass = (status: string) => {
  switch (status) {
    case 'consistent': return 'bg-emerald-500';
    case 'discrepancy': return 'bg-rose-500';
    case 'missing_data': return 'bg-amber-500';
    default: return 'bg-slate-400';
  }
};

const getStatusLabel = (status: string) => {
  switch (status) {
    case 'consistent': return '一致';
    case 'discrepancy': return '金额不符';
    case 'missing_data': return '缺失数据';
    default: return status;
  }
};

const fetchResults = async () => {
  try {
    const data = await api.getReconciliationResults({
      trade_date: globalDate.value,
      status: filterStatus.value || undefined,
      is_resolved: filterResolved.value === '' ? undefined : filterResolved.value === 'true'
    });
    results.value = data;
  } catch (error) {
    console.error('Failed to fetch reconciliation results:', error);
  }
};

const recalculate = async () => {
  isRecalculating.value = true;
  try {
    await api.recalculateDate(globalDate.value);
    alert('重新计算对账完成！');
    fetchResults();
  } catch (error) {
    alert('对账重算失败！');
  } finally {
    isRecalculating.value = false;
  }
};

const exportExcel = () => {
  const url = api.getExportUrl(globalDate.value);
  window.open(url, '_blank');
};

const openAuditModal = (row: ReconciliationResult) => {
  activeRow.value = row;
  auditRemark.value = row.remarks || '';
  auditResolved.value = row.is_resolved;
  showAuditModal.value = true;
};

const saveAudit = async () => {
  if (!activeRow.value) return;
  try {
    const updated = await api.updateReconciliationResult(activeRow.value.id, {
      remarks: auditRemark.value,
      is_resolved: auditResolved.value,
      resolved_by: '财务管理员'
    });
    
    const idx = results.value.findIndex(r => r.id === updated.id);
    if (idx !== -1) {
      results.value[idx] = updated;
    }
    showAuditModal.value = false;
  } catch (error) {
    alert('保存核实说明失败！');
  }
};

watch(globalDate, () => {
  fetchResults();
});

onMounted(() => {
  fetchResults();
});
</script>
