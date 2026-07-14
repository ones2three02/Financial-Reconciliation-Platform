<template>
  <div class="h-[calc(100vh-8rem)] flex flex-col md:flex-row gap-6 overflow-hidden fade-in">
    <!-- Left Sidebar: Overview & Actions -->
    <div class="w-full md:w-80 shrink-0 flex flex-col bg-white border border-slate-200 rounded-xl p-5 shadow-sm justify-between overflow-y-auto">
      <div class="space-y-6">
        <!-- Title & description -->
        <div>
          <div class="flex items-center gap-2 font-bold text-slate-800">
            <ClipboardCheck class="h-5 w-5 text-blue-600" />
            <span class="text-base">{{ globalDate }} 对账概览</span>
          </div>
          <p class="mt-2 text-xs text-slate-400 leading-relaxed">
            完整性优先于金额比较：缺少任一必需来源或存在待确认别名时，结果只能是不完整。
          </p>
        </div>

        <!-- Divider -->
        <div class="h-px bg-slate-100"></div>

        <!-- Metrics List -->
        <div class="space-y-4">
          <!-- Batch Status -->
          <div class="flex items-center justify-between p-1">
            <span class="text-xs font-semibold text-slate-500">批次状态</span>
            <span class="rounded-full px-2.5 py-0.5 text-xs font-bold" :class="batch?.status === 'closed' || batch?.status === 'ready_to_close' ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'">
              {{ batch ? batchStatusLabel(batch.status) : '未创建' }}
            </span>
          </div>

          <!-- Complete Sources -->
          <div 
            @click="activeTab = 'integrity'" 
            class="flex items-center justify-between cursor-pointer hover:bg-slate-50 p-2 -mx-2 rounded-lg transition-colors border border-transparent hover:border-slate-100"
          >
            <span class="text-xs font-semibold text-slate-500">完整来源</span>
            <span class="text-xs font-mono font-extrabold" :class="missingCoverageCount ? 'text-amber-600' : 'text-emerald-600'">
              {{ batch ? `${completeCoverageCount} / ${activeStores.length * sourceCodes.length}` : '—' }}
            </span>
          </div>

          <!-- Pending Issues -->
          <div 
            @click="activeTab = 'issues'" 
            class="flex items-center justify-between cursor-pointer hover:bg-slate-50 p-2 -mx-2 rounded-lg transition-colors border border-transparent hover:border-slate-100"
          >
            <span class="text-xs font-semibold text-slate-500">待处理问题</span>
            <span class="text-xs font-mono font-extrabold" :class="openIssues.length ? 'text-rose-600' : 'text-emerald-600'">
              {{ batch ? openIssues.length : '—' }}
            </span>
          </div>

          <!-- Discrepancies -->
          <div 
            @click="activeTab = 'results'" 
            class="flex items-center justify-between cursor-pointer hover:bg-slate-50 p-2 -mx-2 rounded-lg transition-colors border border-transparent hover:border-slate-100"
          >
            <span class="text-xs font-semibold text-slate-500">金额差异门店</span>
            <span class="text-xs font-mono font-extrabold" :class="discrepancyCount ? 'text-rose-600' : 'text-emerald-600'">
              {{ batch ? discrepancyCount : '—' }}
            </span>
          </div>
        </div>
      </div>

      <div class="space-y-3 mt-6">
        <!-- Actions Toolbar -->
        <div class="h-px bg-slate-100 mb-3"></div>
        
        <div v-if="notice" class="rounded-xl border px-3 py-2 text-[11px] font-semibold mb-2 leading-relaxed" :class="notice.type === 'error' ? 'border-rose-100 bg-rose-50 text-rose-600' : 'border-emerald-100 bg-emerald-50 text-emerald-600'">
          {{ notice.text }}
        </div>
        
        <Button variant="outline" size="sm" class="w-full justify-center text-xs h-9" :disabled="loading" @click="loadWorkspace">
          <RefreshCw class="mr-1.5 h-3.5 w-3.5" /> 刷新数据
        </Button>
        <Button v-if="detail?.results.length" variant="outline" size="sm" class="w-full justify-center text-xs h-9" :disabled="working" @click="downloadReport">
          <FileDown class="mr-1.5 h-3.5 w-3.5" /> 导出结果
        </Button>
        <Button v-if="batch && batch.status !== 'closed' && canOperate" size="sm" class="w-full justify-center text-xs h-9 bg-blue-600 text-white hover:bg-blue-700 shadow-md shadow-blue-500/10" :disabled="working" @click="runReconciliation">
          执行对账
        </Button>
        <Button v-if="batch?.status === 'ready_to_close' && canOperate" size="sm" class="w-full justify-center text-xs h-9 bg-emerald-600 text-white hover:bg-emerald-700 shadow-md shadow-emerald-500/10" :disabled="working" @click="showClose = true">
          确认关账
        </Button>
        <Button v-if="batch?.status === 'closed' && canOperate" variant="outline" size="sm" class="w-full justify-center text-xs h-9 border-amber-300 text-amber-700 hover:bg-amber-50" @click="showReopen = true">
          重开账期
        </Button>
      </div>
    </div>

    <!-- Right Column: Tabbed Tables -->
    <div class="flex-1 min-w-0 flex flex-col gap-4 overflow-hidden">
      <div v-if="!batch" class="flex-1 flex items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center">
        <div>
          <div class="text-sm font-bold text-slate-700">该账期尚未创建批次</div>
          <p class="mt-1.5 text-xs text-slate-500">请先到“文件导入”创建批次并上传工作簿。</p>
        </div>
      </div>

      <template v-else>
        <!-- Tab Controls -->
        <div class="flex border border-slate-200 bg-white rounded-xl p-1 shadow-sm gap-1 shrink-0">
          <button 
            @click="activeTab = 'results'" 
            :class="[
              'flex-1 py-2 text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-1.5',
              activeTab === 'results' 
                ? 'bg-blue-50 text-blue-600 shadow-sm border border-blue-100' 
                : 'text-slate-500 hover:text-slate-800 hover:bg-slate-50 border border-transparent'
            ]"
          >
            <TableProperties class="h-4 w-4" />
            对账差异结果
          </button>
          <button 
            @click="activeTab = 'integrity'" 
            :class="[
              'flex-1 py-2 text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-1.5',
              activeTab === 'integrity' 
                ? 'bg-blue-50 text-blue-600 shadow-sm border border-blue-100' 
                : 'text-slate-500 hover:text-slate-800 hover:bg-slate-50 border border-transparent'
            ]"
          >
            <Grid3X3 class="h-4 w-4" />
            数据来源完整性
          </button>
          <button 
            @click="activeTab = 'issues'" 
            :class="[
              'flex-1 py-2 text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-1.5',
              activeTab === 'issues' 
                ? 'bg-blue-50 text-blue-600 shadow-sm border border-blue-100' 
                : 'text-slate-500 hover:text-slate-800 hover:bg-slate-50 border border-transparent'
            ]"
          >
            <AlertTriangle class="h-4 w-4" />
            待人工确认门店
            <span 
              v-if="openIssues.length" 
              class="rounded-full px-1.5 py-0.5 text-[10px] font-extrabold bg-rose-100 text-rose-700 animate-pulse"
            >
              {{ openIssues.length }}
            </span>
          </button>
        </div>

        <!-- Tab Contents: Source Integrity Matrix -->
        <Card v-if="activeTab === 'integrity'" class="border-slate-200/80 shadow-sm flex-1 flex flex-col overflow-hidden min-h-0 bg-white">
          <CardHeader class="shrink-0 pb-3">
            <CardTitle class="flex items-center gap-2 text-sm"><Grid3X3 class="h-4 w-4 text-blue-600" />来源完整性矩阵</CardTitle>
            <CardDescription class="text-xs text-slate-400">“有数据”和“已确认零”均为完整；“缺失”不能当作 0。确认零收入会记录当前登录人和时间。</CardDescription>
          </CardHeader>
          <CardContent class="flex-1 overflow-auto p-0 min-h-0 border-t border-slate-100">
            <table class="w-full min-w-[850px] text-left text-xs">
              <thead class="sticky top-0 z-10 bg-slate-50 text-[10px] uppercase tracking-wider text-slate-400 border-b border-slate-100">
                <tr>
                  <th class="sticky left-0 top-0 z-30 bg-slate-50 p-3 shadow-[2px_0_4px_rgba(0,0,0,0.02)]">门店</th>
                  <th v-for="source in sourceCodes" :key="source" class="p-3 text-center bg-slate-50">{{ sourceLabel(source) }}</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100">
                <tr v-for="store in activeStores" :key="store.id" class="group hover:bg-slate-50/50">
                  <td class="sticky left-0 z-20 bg-white group-hover:bg-slate-50/50 font-bold text-slate-700 p-3 border-r border-slate-100 shadow-[2px_0_4px_rgba(0,0,0,0.02)]">{{ store.name }}</td>
                  <td v-for="source in sourceCodes" :key="source" class="p-2 text-center">
                    <div class="inline-flex min-w-24 flex-col items-center gap-1 rounded-lg px-2 py-1.5" :class="coverageClass(coverageFor(store.id, source)?.status)">
                      <span class="font-bold">{{ coverageLabel(coverageFor(store.id, source)?.status) }}</span>
                      <span v-if="coverageFor(store.id, source)?.status === 'present_data'" class="font-mono text-[10px]">¥{{ money(coverageFor(store.id, source)?.amount ?? 0) }}</span>
                      <button
                        v-else-if="coverageFor(store.id, source)?.status === 'present_zero' && coverageFor(store.id, source)?.evidence_type === 'manual_zero_confirmation' && batch.status !== 'closed' && canOperate"
                        class="text-[10px] font-bold text-amber-700 underline decoration-dotted"
                        :disabled="working"
                        @click="openZeroRevocation(store, source)"
                      >撤销确认</button>
                      <span v-else-if="coverageFor(store.id, source)?.status === 'present_zero'" class="text-[10px] text-blue-600">文件证明为零</span>
                      <button
                        v-else-if="(!coverageFor(store.id, source) || coverageFor(store.id, source)?.status === 'missing') && batch.status !== 'closed' && canOperate"
                        class="text-[10px] font-bold text-blue-700 underline decoration-dotted"
                        :disabled="working"
                        @click="openZeroConfirmation(store, source)"
                      >确认零收入</button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </CardContent>
        </Card>

        <!-- Tab Contents: Store Alias Mapping -->
        <Card v-if="activeTab === 'issues'" class="border-slate-200/80 shadow-sm flex-1 flex flex-col overflow-hidden min-h-0 bg-white">
          <CardHeader class="shrink-0 pb-3">
            <CardTitle class="flex items-center gap-2 text-sm"><AlertTriangle class="h-4 w-4 text-blue-600" />待人工确认门店</CardTitle>
            <CardDescription class="text-xs text-slate-400">系统不会依据名称相似度自动归店。请核对来源和原始名称后，由管理员明确选择标准门店。</CardDescription>
          </CardHeader>
          <CardContent class="flex-1 overflow-auto min-h-0 p-5 border-t border-slate-100">
            <div v-if="!openIssues.length" class="h-full flex items-center justify-center text-center">
              <div>
                <div class="text-sm font-bold text-emerald-600">暂无待确认门店</div>
                <p class="mt-1 text-xs text-slate-500">所有第三方账单内的店名均已正确映射为标准门店。</p>
              </div>
            </div>
            <div v-else class="space-y-3">
              <div v-for="issue in openIssues" :key="issue.id" class="grid items-center gap-3 rounded-xl border border-amber-200 bg-amber-50/50 p-4 md:grid-cols-[1fr_1fr_auto]">
                <div>
                  <div class="text-[10px] font-bold uppercase tracking-wider text-amber-600">{{ sourceLabel(issue.source_code) }} · {{ issue.issue_type }}</div>
                  <div class="mt-1 text-sm font-extrabold text-slate-800">{{ issue.raw_value || '空门店名称' }}</div>
                  <div class="mt-1 text-[11px] text-slate-500">影响 {{ issue.affected_row_count }} 行，金额 ¥{{ money(issue.affected_amount) }}</div>
                </div>
                <Select v-model="issueStoreSelections[issue.id]" :options="activeStores.map((store) => ({ value: store.id, label: store.name }))" placeholder="选择确认归属的标准门店" />
                <Button size="sm" :disabled="!issueStoreSelections[issue.id] || working || !canConfirmAlias" @click="confirmIssueAlias(issue)">确认映射</Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <!-- Tab Contents: Store Reconciliation Results -->
        <Card v-if="activeTab === 'results'" class="border-slate-200/80 shadow-sm flex-1 flex flex-col overflow-hidden min-h-0 bg-white">
          <CardHeader class="shrink-0 pb-3">
            <CardTitle class="flex items-center gap-2 text-sm"><TableProperties class="h-4 w-4 text-blue-600" />门店对账结果</CardTitle>
            <CardDescription class="text-xs text-slate-400">差异 =（通联 + 美团 + 抖音）-（销售收入 - 现金）。差异项填写核实说明并标记处理后才可关账。</CardDescription>
          </CardHeader>
          <CardContent class="flex-1 overflow-auto p-0 min-h-0 border-t border-slate-100">
            <table class="w-full min-w-[1100px] text-left text-xs">
              <thead class="sticky top-0 z-10 bg-slate-50 text-[10px] uppercase tracking-wider text-slate-400 border-b border-slate-100">
                <tr>
                  <th class="sticky left-0 top-0 z-30 bg-slate-50 p-3 shadow-[2px_0_4px_rgba(0,0,0,0.02)]">门店</th>
                  <th class="p-3 text-right bg-slate-50">通联</th>
                  <th class="p-3 text-right bg-slate-50">美团</th>
                  <th class="p-3 text-right bg-slate-50">抖音</th>
                  <th class="p-3 text-right bg-slate-50">现金</th>
                  <th class="p-3 text-right bg-slate-50">销售</th>
                  <th class="p-3 text-right bg-slate-50">差异</th>
                  <th class="p-3 text-center bg-slate-50">状态</th>
                  <th class="p-3 bg-slate-50">核实说明</th>
                  <th class="p-3 text-center bg-slate-50">操作</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100">
                <tr v-if="!detail?.results.length"><td colspan="10" class="p-10 text-center text-slate-400 bg-white">尚未执行对账</td></tr>
                <tr v-for="result in detail?.results ?? []" :key="result.id" class="group hover:bg-slate-50/50">
                  <td class="sticky left-0 z-20 bg-white group-hover:bg-slate-50/50 font-bold text-slate-700 p-3 border-r border-slate-100 shadow-[2px_0_4px_rgba(0,0,0,0.02)]">{{ result.standard_store_name }}</td>
                  <td class="p-3 text-right font-mono">{{ money(result.tonglian_amount) }}</td>
                  <td class="p-3 text-right font-mono">{{ money(result.meituan_amount) }}</td>
                  <td class="p-3 text-right font-mono">{{ money(result.douyin_amount) }}</td>
                  <td class="p-3 text-right font-mono">{{ money(result.cash_amount) }}</td>
                  <td class="p-3 text-right font-mono">{{ money(result.sales_amount) }}</td>
                  <td class="p-3 text-right font-mono font-extrabold" :class="result.status === 'consistent' ? 'text-emerald-600' : 'text-rose-600'">{{ signedMoney(result.difference) }}</td>
                  <td class="p-3 text-center"><span class="rounded-full px-2 py-1 text-[10px] font-bold" :class="resultStatusClass(result.status)">{{ resultStatusLabel(result.status) }}</span></td>
                  <td class="max-w-64 truncate p-3 text-slate-500" :title="result.remarks || ''">{{ result.remarks || '—' }}</td>
                  <td class="p-3 text-center"><Button v-if="result.status === 'discrepancy' && canOperate" variant="ghost" size="xs" class="text-blue-700" @click="openResolution(result)">{{ result.is_resolved ? '修改说明' : '处理差异' }}</Button></td>
                </tr>
              </tbody>
            </table>
          </CardContent>
        </Card>
      </template>
    </div>

    <!-- Global Modals Teleported to body -->
    <Teleport to="body">
      <div v-if="zeroConfirmation" class="fixed inset-0 z-50 flex items-center justify-center bg-zinc-950/40 p-4 backdrop-blur-sm" @click.self="zeroConfirmation = null">
        <Card class="w-full max-w-md bg-white shadow-2xl">
          <CardHeader>
            <CardTitle class="text-base">确认该来源确实为零收入</CardTitle>
            <CardDescription>这是业务确认，不是把缺失数据自动当成 0；确认后会记录当前登录人和时间。</CardDescription>
          </CardHeader>
          <CardContent class="space-y-3 text-sm">
            <div class="grid grid-cols-[88px_1fr] gap-2 rounded-xl bg-slate-50 p-4">
              <span class="text-slate-500">账期</span><strong>{{ globalDate }}</strong>
              <span class="text-slate-500">门店</span><strong>{{ zeroConfirmation.storeName }}</strong>
              <span class="text-slate-500">收入来源</span><strong>{{ sourceLabel(zeroConfirmation.source) }}</strong>
            </div>
            <div class="rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs font-semibold text-amber-800">请再次核对：数据“缺失”不等于“零收入”。只有确认该门店当天此来源确实没有收入时才能继续。</div>
          </CardContent>
          <CardFooter class="justify-end gap-3">
            <Button variant="outline" :disabled="working" @click="zeroConfirmation = null">取消</Button>
            <Button class="bg-blue-600 text-white hover:bg-blue-700" :disabled="working" @click="confirmSourceZero">我已核对，确认零收入</Button>
          </CardFooter>
        </Card>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="zeroRevocation" class="fixed inset-0 z-50 flex items-center justify-center bg-zinc-950/40 p-4 backdrop-blur-sm" @click.self="closeZeroRevocation">
        <Card class="w-full max-w-md bg-white shadow-2xl">
          <CardHeader>
            <CardTitle class="text-base">撤销零收入确认</CardTitle>
            <CardDescription>撤销后，{{ zeroRevocation.storeName }}的{{ sourceLabel(zeroRevocation.source) }}将恢复为“缺失”，对账结果会立即变为不完整。</CardDescription>
          </CardHeader>
          <CardContent class="space-y-3">
            <div class="rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">账期：{{ globalDate }}。该操作不会删除历史记录，原确认和本次撤销都会保留在审计日志中。</div>
            <textarea v-model="zeroRevokeReason" rows="4" maxlength="500" class="w-full rounded-xl border border-slate-200 p-3 text-sm outline-none focus:ring-2 focus:ring-amber-500" placeholder="请填写撤销原因，例如：刚才误触，实际文件尚未导出"></textarea>
          </CardContent>
          <CardFooter class="justify-end gap-3">
            <Button variant="outline" :disabled="working" @click="closeZeroRevocation">取消</Button>
            <Button class="bg-amber-600 text-white hover:bg-amber-700" :disabled="working || !zeroRevokeReason.trim()" @click="revokeSourceZero">确认撤销</Button>
          </CardFooter>
        </Card>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="activeResult" class="fixed inset-0 z-50 flex items-center justify-center bg-zinc-950/40 p-4 backdrop-blur-sm" @click.self="activeResult = null">
        <Card class="w-full max-w-lg bg-white shadow-2xl">
          <CardHeader><CardTitle class="text-base">处理 {{ activeResult.standard_store_name }} 差异</CardTitle><CardDescription>当前差异 {{ signedMoney(activeResult.difference) }}。请填写实际核实结论，不要只写“已处理”。</CardDescription></CardHeader>
          <CardContent class="space-y-4">
            <textarea v-model="resolutionRemark" rows="5" maxlength="1000" class="w-full rounded-xl border border-slate-200 p-3 text-sm outline-none focus:ring-2 focus:ring-blue-500" placeholder="例如：门店销售表漏录一笔，已联系门店于次日补录……"></textarea>
            <label class="flex items-center gap-2 text-xs font-bold text-slate-700"><input v-model="resolutionDone" type="checkbox" /> 已核实并完成处理</label>
          </CardContent>
          <CardFooter class="justify-end gap-3"><Button variant="outline" @click="activeResult = null">取消</Button><Button :disabled="working || !resolutionRemark.trim()" @click="saveResolution">保存说明</Button></CardFooter>
        </Card>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="showReopen" class="fixed inset-0 z-50 flex items-center justify-center bg-zinc-950/40 p-4 backdrop-blur-sm" @click.self="showReopen = false">
        <Card class="w-full max-w-md bg-white shadow-2xl">
          <CardHeader><CardTitle class="text-base">重开已关账批次</CardTitle><CardDescription>重开会增加批次版本并写入审计记录，必须填写具体原因。</CardDescription></CardHeader>
          <CardContent><textarea v-model="reopenReason" rows="4" maxlength="500" class="w-full rounded-xl border border-slate-200 p-3 text-sm outline-none focus:ring-2 focus:ring-amber-500" placeholder="请输入重开原因"></textarea></CardContent>
          <CardFooter class="justify-end gap-3"><Button variant="outline" @click="showReopen = false">取消</Button><Button class="bg-amber-600 text-white hover:bg-amber-700" :disabled="working || !reopenReason.trim()" @click="reopenCurrentBatch">确认重开</Button></CardFooter>
        </Card>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="showClose" class="fixed inset-0 z-50 flex items-center justify-center bg-zinc-950/40 p-4 backdrop-blur-sm" @click.self="showClose = false">
        <Card class="w-full max-w-md bg-white shadow-2xl">
          <CardHeader><CardTitle class="text-base">确认关账 {{ globalDate }}</CardTitle><CardDescription>关账后该账期的导入、确认零、门店映射重提和重新对账都会被锁定；如需修改，必须填写原因重开。</CardDescription></CardHeader>
          <CardContent><div class="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-xs font-semibold text-emerald-800">请确认当前所有来源完整、金额差异已核实，且账期日期无误。</div></CardContent>
          <CardFooter class="justify-end gap-3"><Button variant="outline" :disabled="working" @click="showClose = false">取消</Button><Button class="bg-emerald-600 text-white hover:bg-emerald-700" :disabled="working" @click="closeCurrentBatch">我已核对，确认关账</Button></CardFooter>
        </Card>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { AlertTriangle, ClipboardCheck, FileDown, Grid3X3, RefreshCw, TableProperties } from 'lucide-vue-next';
import { api, getSession } from '../services/api';
import type { BatchDetail, DataQualityIssue, ReconciliationBatch, ReconciliationResult, SourceCode, Store, StoreAlias } from '../services/api';
import { globalDate } from '../services/store';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '../components/ui/card';
import { Select } from '../components/ui/select';

const sourceCodes: SourceCode[] = ['tonglian', 'meituan', 'douyin', 'cash', 'sales'];
const stores = ref<Store[]>([]);
const aliases = ref<StoreAlias[]>([]);
const batch = ref<ReconciliationBatch | null>(null);
const detail = ref<BatchDetail | null>(null);
const loading = ref(false);
const working = ref(false);
const notice = ref<{ type: 'success' | 'error'; text: string } | null>(null);
const issueStoreSelections = reactive<Record<number, number | null>>({});
const activeResult = ref<ReconciliationResult | null>(null);
const resolutionRemark = ref('');
const resolutionDone = ref(false);
const showReopen = ref(false);
const showClose = ref(false);
const reopenReason = ref('');
const activeTab = ref<'results' | 'integrity' | 'issues'>('results');
type ZeroAction = { storeId: number; storeName: string; source: SourceCode };
const zeroConfirmation = ref<ZeroAction | null>(null);
const zeroRevocation = ref<ZeroAction | null>(null);
const zeroRevokeReason = ref('');

const activeStores = computed(() => stores.value.filter((store) => store.is_active));
const canOperate = computed(() => ['admin', 'finance'].includes(getSession().role ?? ''));
const canConfirmAlias = computed(() => getSession().role === 'admin');
const openIssues = computed(() => detail.value?.quality_issues.filter((issue) => issue.status === 'open') ?? []);
const completeCoverageCount = computed(() => detail.value?.coverages.filter((coverage) => ['present_data', 'present_zero'].includes(coverage.status)).length ?? 0);
const missingCoverageCount = computed(() => Math.max(0, activeStores.value.length * sourceCodes.length - completeCoverageCount.value));
const discrepancyCount = computed(() => detail.value?.results.filter((result) => result.status === 'discrepancy' && !result.is_resolved).length ?? 0);

const loadWorkspace = async () => {
  loading.value = true;
  notice.value = null;
  try {
    const [storeRows, batchRows, aliasRows] = await Promise.all([api.getStores(), api.getBatches(), api.getStoreAliases('pending')]);
    stores.value = storeRows;
    aliases.value = aliasRows;
    batch.value = batchRows.find((item) => item.business_date === globalDate.value) ?? null;
    detail.value = batch.value ? await api.getBatchDetail(batch.value.id) : null;
  } catch (error) {
    notice.value = { type: 'error', text: errorDetail(error) };
  } finally {
    loading.value = false;
  }
};

const coverageFor = (storeId: number, source: SourceCode) => detail.value?.coverages.find((item) => item.store_id === storeId && item.source_code === source);

const openZeroConfirmation = (store: Store, source: SourceCode) => {
  zeroConfirmation.value = { storeId: store.id, storeName: store.name, source };
};

const confirmSourceZero = async () => {
  if (!batch.value || !zeroConfirmation.value) return;
  const action = zeroConfirmation.value;
  working.value = true;
  try {
    await api.confirmZero(batch.value.id, action.storeId, action.source);
    zeroConfirmation.value = null;
    notice.value = { type: 'success', text: `已确认 ${action.storeName}的${sourceLabel(action.source)}为零收入，操作已写入审计记录。` };
    detail.value = await api.getBatchDetail(batch.value.id);
  } catch (error) {
    notice.value = { type: 'error', text: errorDetail(error) };
  } finally {
    working.value = false;
  }
};

const openZeroRevocation = (store: Store, source: SourceCode) => {
  zeroRevocation.value = { storeId: store.id, storeName: store.name, source };
  zeroRevokeReason.value = '';
};

const closeZeroRevocation = () => {
  if (working.value) return;
  zeroRevocation.value = null;
  zeroRevokeReason.value = '';
};

const revokeSourceZero = async () => {
  if (!batch.value || !zeroRevocation.value || !zeroRevokeReason.value.trim()) return;
  const action = zeroRevocation.value;
  working.value = true;
  try {
    await api.revokeZero(
      batch.value.id,
      action.storeId,
      action.source,
      zeroRevokeReason.value.trim(),
    );
    zeroRevocation.value = null;
    zeroRevokeReason.value = '';
    detail.value = await api.getBatchDetail(batch.value.id);
    batch.value = detail.value.batch;
    notice.value = { type: 'success', text: `已撤销 ${action.storeName}的${sourceLabel(action.source)}零收入确认，当前恢复为数据缺失。` };
  } catch (error) {
    notice.value = { type: 'error', text: errorDetail(error) };
  } finally {
    working.value = false;
  }
};

const confirmIssueAlias = async (issue: DataQualityIssue) => {
  const storeId = issueStoreSelections[issue.id];
  const alias = aliases.value.find((item) => item.source_code === issue.source_code && item.alias_name === issue.raw_value);
  if (!storeId || !alias) {
    notice.value = { type: 'error', text: '没有找到与该质量问题对应的待确认别名，请刷新后重试。' };
    return;
  }
  if (getSession().role !== 'admin') {
    notice.value = { type: 'error', text: '门店别名确认需要管理员权限。' };
    return;
  }
  working.value = true;
  try {
    await api.confirmStoreAlias(alias.id, storeId);
    notice.value = { type: 'success', text: `已将“${alias.alias_name}”明确绑定到所选标准门店，并重新提取受影响文件。` };
    await loadWorkspace();
  } catch (error) {
    notice.value = { type: 'error', text: errorDetail(error) };
  } finally {
    working.value = false;
  }
};

const runReconciliation = async () => {
  if (!batch.value) return;
  working.value = true;
  try {
    await api.reconcileBatch(batch.value.id);
    detail.value = await api.getBatchDetail(batch.value.id);
    batch.value = detail.value.batch;
    notice.value = { type: 'success', text: '对账已按当前完整性和金额重新计算。' };
  } catch (error) {
    notice.value = { type: 'error', text: errorDetail(error) };
  } finally {
    working.value = false;
  }
};

const closeCurrentBatch = async () => {
  if (!batch.value) return;
  working.value = true;
  try {
    batch.value = await api.closeBatch(batch.value.id);
    detail.value = await api.getBatchDetail(batch.value.id);
    showClose.value = false;
    notice.value = { type: 'success', text: '该账期已关账，后续修改需先填写原因并重开。' };
  } catch (error) {
    notice.value = { type: 'error', text: errorDetail(error) };
  } finally {
    working.value = false;
  }
};

const reopenCurrentBatch = async () => {
  if (!batch.value || !reopenReason.value.trim()) return;
  working.value = true;
  try {
    batch.value = await api.reopenBatch(batch.value.id, reopenReason.value.trim());
    detail.value = await api.getBatchDetail(batch.value.id);
    showReopen.value = false;
    reopenReason.value = '';
    notice.value = { type: 'success', text: '批次已重开并增加版本，可以补充文件后重新对账。' };
  } catch (error) {
    notice.value = { type: 'error', text: errorDetail(error) };
  } finally {
    working.value = false;
  }
};

const openResolution = (result: ReconciliationResult) => {
  activeResult.value = result;
  resolutionRemark.value = result.remarks ?? '';
  resolutionDone.value = result.is_resolved;
};

const saveResolution = async () => {
  if (!activeResult.value) return;
  working.value = true;
  try {
    await api.updateReconciliationResult(activeResult.value.id, { remarks: resolutionRemark.value.trim(), is_resolved: resolutionDone.value });
    activeResult.value = null;
    if (batch.value) {
      await api.reconcileBatch(batch.value.id);
      detail.value = await api.getBatchDetail(batch.value.id);
      batch.value = detail.value.batch;
    }
    notice.value = { type: 'success', text: '差异核实说明已保存。' };
  } catch (error) {
    notice.value = { type: 'error', text: errorDetail(error) };
  } finally {
    working.value = false;
  }
};

const downloadReport = async () => {
  working.value = true;
  try {
    const blob = await api.downloadReconciliation(globalDate.value);
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `对账结果_${globalDate.value}.xlsx`;
    link.click();
    URL.revokeObjectURL(url);
  } catch (error) {
    notice.value = { type: 'error', text: errorDetail(error) };
  } finally {
    working.value = false;
  }
};

const sourceLabel = (source: string) => ({ tonglian: '通联', meituan: '美团', douyin: '抖音', cash: '现金', sales: '销售收入', finance: '财务表', store_finance: '门店财务表' }[source] ?? source);
const coverageLabel = (status?: string) => ({ present_data: '有数据', present_zero: '已确认零', missing: '缺失', attention_required: '待处理' }[status ?? 'missing'] ?? '缺失');
const coverageClass = (status?: string) => status === 'present_data' ? 'bg-emerald-50 text-emerald-700' : status === 'present_zero' ? 'bg-blue-50 text-blue-700' : status === 'attention_required' ? 'bg-amber-50 text-amber-700' : 'bg-rose-50 text-rose-700';
const batchStatusLabel = (status: string) => ({ draft: '草稿', attention_required: '待处理', ready_to_close: '可关账', closed: '已关账' }[status] ?? status);
const resultStatusLabel = (status: string) => ({ consistent: '一致', discrepancy: '金额差异', incomplete: '数据不完整', missing_data: '数据不完整' }[status] ?? status);
const resultStatusClass = (status: string) => status === 'consistent' ? 'bg-emerald-50 text-emerald-700' : status === 'discrepancy' ? 'bg-rose-50 text-rose-700' : 'bg-amber-50 text-amber-700';
const money = (value: number) => Number(value).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const signedMoney = (value: number) => `${Number(value) > 0 ? '+' : ''}¥${money(value)}`;
const errorDetail = (error: unknown) => (error as { response?: { data?: { detail?: string } }; message?: string }).response?.data?.detail || (error as { message?: string }).message || '操作失败';

watch(globalDate, () => { void loadWorkspace(); });
onMounted(loadWorkspace);
</script>
