<template>
  <div class="space-y-8 fade-in">
    <!-- Filter & Action Bar -->
    <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 flex flex-wrap items-center justify-between gap-4">
      <div class="flex flex-wrap items-center gap-4">
        <!-- Date Filter -->
        <div class="flex flex-col gap-1">
          <label for="filter-date" class="text-xs font-semibold text-slate-400 uppercase tracking-wider">账期日期</label>
          <input 
            id="filter-date"
            type="date" 
            v-model="filterDate" 
            @change="fetchResults"
            class="border border-slate-200 rounded-xl px-4 py-2 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <!-- Status Filter -->
        <div class="flex flex-col gap-1">
          <label for="filter-status" class="text-xs font-semibold text-slate-400 uppercase tracking-wider">比对状态</label>
          <select 
            id="filter-status"
            v-model="filterStatus" 
            @change="fetchResults"
            class="border border-slate-200 rounded-xl px-4 py-2 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
          >
            <option value="">全部</option>
            <option value="consistent">一致 (Consistent)</option>
            <option value="discrepancy">有差异 (Discrepancy)</option>
            <option value="missing_data">缺失数据 (Missing)</option>
          </select>
        </div>

        <!-- Resolution Filter -->
        <div class="flex flex-col gap-1">
          <label for="filter-resolved" class="text-xs font-semibold text-slate-400 uppercase tracking-wider">核实处理</label>
          <select 
            id="filter-resolved"
            v-model="filterResolved" 
            @change="fetchResults"
            class="border border-slate-200 rounded-xl px-4 py-2 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
          >
            <option value="">全部</option>
            <option value="false">未处理</option>
            <option value="true">已标记处理</option>
          </select>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="flex items-center gap-3 self-end">
        <button 
          @click="recalculate"
          class="px-4 py-2 border border-blue-200 text-blue-600 rounded-xl text-sm font-semibold hover:bg-blue-50 transition-colors disabled:opacity-50"
          :disabled="isRecalculating"
        >
          ⚡ {{ isRecalculating ? '重算中...' : '重新对账' }}
        </button>
        <button 
          @click="exportExcel"
          class="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-sm font-semibold shadow-md shadow-emerald-500/20 transition-all flex items-center gap-2"
        >
          📥 导出 Excel 报表
        </button>
      </div>
    </div>

    <!-- Main Results Table -->
    <div class="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-slate-50 text-slate-400 text-xs font-semibold uppercase tracking-wider border-b border-slate-100">
              <th class="p-4">标准门店</th>
              <th class="p-4 text-right">销售系统 (S)</th>
              <th class="p-4 text-right">交班现金 (C)</th>
              <th class="p-4 text-right">应收 (S - C)</th>
              <th class="p-4 text-right">后台实收汇总 (P)</th>
              <th class="p-4 text-right">差异额 (P - 应收)</th>
              <th class="p-4 text-center">状态</th>
              <th class="p-4">核实说明</th>
              <th class="p-4 text-center">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 text-sm">
            <tr v-if="results.length === 0">
              <td colspan="9" class="p-8 text-center text-slate-400 text-sm">此账期日期暂无对账明细。请确保已导入当日文件。</td>
            </tr>
            <tr 
              v-for="r in results" 
              :key="r.id"
              class="hover:bg-slate-50/50 transition-colors"
              :class="{'bg-rose-50/10': r.status === 'discrepancy' && !r.is_resolved}"
            >
              <td class="p-4 font-bold text-slate-700">{{ r.standard_store_name }}</td>
              <td class="p-4 text-right font-medium text-slate-600">¥{{ Number(r.sales_amount).toFixed(2) }}</td>
              <td class="p-4 text-right font-medium text-slate-600">¥{{ Number(r.cash_amount).toFixed(2) }}</td>
              <td class="p-4 text-right font-bold text-slate-700 bg-slate-50/20">
                ¥{{ Number(r.actual_amount).toFixed(2) }}
              </td>
              <td class="p-4 text-right font-bold text-slate-700" title="通联+美团+抖音">
                ¥{{ Number(r.expected_amount).toFixed(2) }}
              </td>
              <td class="p-4 text-right font-bold" :class="getDifferenceClass(r)">
                {{ getDifferencePrefix(r.difference) }}¥{{ Math.abs(r.difference).toFixed(2) }}
              </td>
              <td class="p-4 text-center">
                <span 
                  class="px-2.5 py-1 rounded-full text-xs font-semibold"
                  :class="getStatusBadgeClass(r.status)"
                >
                  {{ getStatusLabel(r.status) }}
                </span>
              </td>
              <td class="p-4 max-w-xs truncate text-slate-500" :title="r.remarks || ''">
                {{ r.remarks || '—' }}
              </td>
              <td class="p-4 text-center">
                <button 
                  @click="openAuditModal(r)"
                  class="px-3 py-1.5 border border-slate-200 rounded-lg text-xs font-semibold hover:bg-slate-50 hover:text-blue-600 transition-colors"
                >
                  📝 核实备注
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Audit Modal -->
    <div 
      v-if="showAuditModal" 
      class="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4 fade-in"
      @click.self="showAuditModal = false"
    >
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-lg overflow-hidden border border-slate-100">
        <!-- Modal Header -->
        <div class="px-6 py-4 bg-slate-50 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h3 class="font-bold text-slate-900 text-base">核实处理: {{ activeRow?.standard_store_name }}</h3>
            <p class="text-xs text-slate-500">账期: {{ activeRow?.trade_date }}</p>
          </div>
          <button @click="showAuditModal = false" class="text-slate-400 hover:text-slate-600 text-lg">×</button>
        </div>

        <!-- Modal Body -->
        <div class="p-6 space-y-6">
          <!-- Summary Box -->
          <div class="grid grid-cols-2 gap-4 p-4 bg-slate-50 rounded-xl border border-slate-100 text-sm">
            <div>
              <span class="text-xs text-slate-400 block mb-0.5">销售应收(销售-现金)</span>
              <span class="font-bold text-slate-700">¥{{ activeRow ? Number(activeRow.actual_amount).toFixed(2) : '0.00' }}</span>
            </div>
            <div>
              <span class="text-xs text-slate-400 block mb-0.5">后台实收汇总</span>
              <span class="font-bold text-slate-700">¥{{ activeRow ? Number(activeRow.expected_amount).toFixed(2) : '0.00' }}</span>
            </div>
            <div class="col-span-2 border-t border-slate-200/60 pt-2 flex items-center justify-between">
              <span class="text-xs font-semibold text-slate-500">账面偏差值</span>
              <span class="font-bold" :class="activeRow ? getDifferenceClass(activeRow) : ''">
                ¥{{ activeRow ? Number(activeRow.difference).toFixed(2) : '0.00' }}
              </span>
            </div>
          </div>

          <!-- Audit Inputs -->
          <div class="space-y-4">
            <div class="flex flex-col gap-1.5">
              <label for="audit-remark" class="text-xs font-bold text-slate-500 uppercase tracking-wider">处理备注/原因分析</label>
              <textarea 
                id="audit-remark"
                v-model="auditRemark" 
                rows="3" 
                placeholder="例如: 财务核实杨一一店因美团退款未及时入账导致差异，明日对账自动结平。"
                class="border border-slate-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              ></textarea>
            </div>

            <div class="flex items-center gap-2">
              <input 
                id="is-resolved-cb"
                type="checkbox" 
                v-model="auditResolved" 
                class="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
              />
              <label for="is-resolved-cb" class="text-sm font-semibold text-slate-700 cursor-pointer">
                已核实并标记解决 (Resolved)
              </label>
            </div>
          </div>
        </div>

        <!-- Modal Footer -->
        <div class="px-6 py-4 bg-slate-50 border-t border-slate-100 flex justify-end gap-3">
          <button 
            @click="showAuditModal = false"
            class="px-4 py-2 border border-slate-200 text-slate-600 rounded-xl text-sm font-semibold hover:bg-slate-100 transition-colors"
          >
            取消
          </button>
          <button 
            @click="saveAudit"
            class="px-5 py-2 bg-blue-600 text-white rounded-xl text-sm font-semibold hover:bg-blue-700 shadow-md shadow-blue-500/20 transition-all"
          >
            保存并返回
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { api } from '../services/api';
import type { ReconciliationResult } from '../services/api';

const getTodayStr = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};

// Filter states
const filterDate = ref(getTodayStr());
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
    case 'consistent': return 'bg-emerald-50 text-emerald-600';
    case 'discrepancy': return 'bg-rose-50 text-rose-600';
    case 'missing_data': return 'bg-amber-50 text-amber-600';
    default: return 'bg-slate-100 text-slate-600';
  }
};

const getStatusLabel = (status: string) => {
  switch (status) {
    case 'consistent': return '一致';
    case 'discrepancy': return '异常差异';
    case 'missing_data': return '缺失数据';
    default: return status;
  }
};

const fetchResults = async () => {
  try {
    const data = await api.getReconciliationResults({
      trade_date: filterDate.value,
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
    await api.recalculateDate(filterDate.value);
    alert('重新计算对账完成！');
    fetchResults();
  } catch (error) {
    alert('对账重算失败！');
  } finally {
    isRecalculating.value = false;
  }
};

const exportExcel = () => {
  const url = api.getExportUrl(filterDate.value);
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
    
    // Update local list row
    const idx = results.value.findIndex(r => r.id === updated.id);
    if (idx !== -1) {
      results.value[idx] = updated;
    }
    showAuditModal.value = false;
  } catch (error) {
    alert('保存核实说明失败！');
  }
};

onMounted(() => {
  fetchResults();
});
</script>
