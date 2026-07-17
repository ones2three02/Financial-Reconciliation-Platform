import { ref } from 'vue';

export interface TourStep {
  targetSelector: string;
  title: string;
  content: string;
}

export const isTourActive = ref(false);
export const tourSteps = ref<TourStep[]>([]);
export const currentStepIndex = ref(0);
export const activePageTour = ref<'dashboard' | 'reconciliation' | 'import' | 'stores' | 'mappings' | null>(null);

export const startTour = (page: 'dashboard' | 'reconciliation' | 'import' | 'stores' | 'mappings') => {
  activePageTour.value = page;
  currentStepIndex.value = 0;
  
  if (page === 'dashboard') {
    tourSteps.value = [
      {
        targetSelector: '#global-date-selector',
        title: '全局账期选择器',
        content: '在此处切换全局对账日期。整个平台（看板、文件导入、明细对账）的数据均以此账期为基准自动进行联动切换，保障历史对账数据的追溯完整性。'
      },
      {
        targetSelector: '#dashboard-metrics-summary',
        title: '今日对账核心指标',
        content: '这里实时汇总今日对账的核心指标，包括：对账门店总数、账目一致率、异常或缺失的门店数，以及今日发生差异的偏差金额总计。点击卡片可快速了解本日对账整体概况。'
      },
      {
        targetSelector: '#dashboard-trends-card',
        title: '连续账期核验面板',
        content: '支持切换‘最近7天’和‘整月日历’两种模式。日历以颜色区分账期状态（绿色为正常已关账，黄色为待处理，红色为异常差异，灰色为未建批次），点击任意日期卡片可一键切换全局账期。'
      },
      {
        targetSelector: '#dashboard-chart-card',
        title: '近 7 天销售与实收趋势比对',
        content: '展示实收金额与销售应收的对比趋势图表。平直的线条代表对账状态平稳，任何明显的起伏和偏离都在提醒财务人员该账期存在大额对账偏差。'
      },
      {
        targetSelector: '#dashboard-discrepancy-stores',
        title: '当前差异排行 (Top 5)',
        content: '这里是本日对账差异最为严重的 5 家门店榜单。排序按差异绝对值从大到小排列，方便您直观发现问题，点击‘去核实’即可一键直达处理该店对账明细。'
      },
      {
        targetSelector: '#sidebar-heartbeat-status',
        title: '本地安全沙箱心跳状态',
        content: '这个闪烁的绿灯代表前端与 Python 离线计算引擎之间的本地 TCP 通信完全畅通。系统已通过系统托盘自动保活，所有敏感财务流水均在本地沙箱中闭环处理，100% 杜绝了外泄风险。'
      }
    ];
  } else if (page === 'reconciliation') {
    tourSteps.value = [
      {
        targetSelector: '#reconciliation-overview-header',
        title: '对账控制中心',
        content: '这里是您每日关账的工作大厅。对账要求“完整性优先于金额比对”，必须确保各渠道的数据来源完整、所有未知别名皆已匹配绑定后，才能执行最终对账和关账。'
      },
      {
        targetSelector: '#issues-tab-btn',
        title: '第一步：人工确认门店别名',
        content: '当账单中出现新增店名或三方渠道新分配的非标名称时，系统无法归类。您需要在此页签中手动将其绑定到集团的标准门店，绑定一次后系统便会长久智能识别。'
      },
      {
        targetSelector: '#integrity-tab-btn',
        title: '第二步：核对数据来源完整性',
        content: '在此确认每个门店的各渠道报表是否都已成功导入。如果该店当天由于暂停营业确实无实收流水，在此点击‘确认零收入’确认，否则系统将因数据缺失拒绝关账，防范漏账。'
      },
      {
        targetSelector: '#results-tab-btn',
        title: '第三步：金额对账差异结果',
        content: '对账计算完成后，在此查看各店交易明细与金额比对。如果出现差额（如顾客发生退款、多扣手续费等），双击差异条目即可记录详细的“核实说明”，确保账期合规可查。'
      },
      {
        targetSelector: '#reconciliation-sidebar-actions',
        title: '第四步：执行对账与确认关账',
        content: '数据备齐后，点击‘执行对账’启动本地引擎重新核算。当所有差异都被合理标注并确认无误后，点击‘确认关账’永久锁定今日账期。如果需要二次修改，可在下方点击‘重开账期’。'
      }
    ];
  } else if (page === 'import') {
    tourSteps.value = [
      {
        targetSelector: '#import-upload-card',
        title: '数据采集中心',
        content: '这里是财务对账的核心导入入口。我们建议您按步骤进行模板选择和导入，支持对导入记录进行回滚管理。'
      },
      {
        targetSelector: '#import-template-card',
        title: '1. 选择工作簿模板',
        content: '第一步：选择需要导入的账单模板（如美团、抖音、通联等）。系统会根据所选模板的版本规则精确读取表头，拒绝猜测。特定模板（如门店财务表）会要求您指定属于哪一家具体的标准门店。'
      },
      {
        targetSelector: '#import-file-card',
        title: '2. 选择并秒速拖拽导入',
        content: '第二步：在选好模板后，直接将对应的 Excel 交易账单拖入此虚线框内。桌面端已深度适配，支持拖拽批量自动解析并送入预检队列，无需再费力在文件选择器里寻找，更加方便！'
      },
      {
        targetSelector: '#import-history-card',
        title: '当前批次导入记录',
        content: '第三步：这里展示当日批次下所有已导入的渠道报表文件。如果发现上传错误，支持点击“替换文件”或“作废文件”来进行冲正，保证历史记录的整洁性。'
      }
    ];
  } else if (page === 'stores') {
    tourSteps.value = [
      {
        targetSelector: '#store-tab-controls',
        title: '门店配置页签切换',
        content: '这是系统对账和别称识别的核心规则库。您可以在这里切换‘标准门店管理’和‘别名名称绑定’两个功能页面。'
      },
      {
        targetSelector: '#store-list-card',
        title: '集团官方标准门店库',
        content: '这里是集团官方的标准门店列表。您可以在这里创建新店、编辑基本资料（区域、负责人、联系电话），或者对停业转让的门店点击‘停用’以停止其对账流程。'
      },
      {
        targetSelector: '#store-alias-card',
        title: '三方渠道店名别称映射',
        content: '这里记录了各三方交易渠道 Excel 中的原始店名与系统标准店名之间的转换字典。绑定后，系统会自动根据它识别文件归属，彻底根除三方店名混乱问题。'
      }
    ];
  } else if (page === 'mappings') {
    tourSteps.value = [
      {
        targetSelector: '#mapping-create-card',
        title: '新建列头字段映射规则',
        content: '这是新建列头映射规则的表单区域。您可以选择‘系统标准字段’（如交易时间、实收金额），并在下方输入 Excel 中的‘原始字段列头名称’（如通联的‘交易金额(元)’），点击保存即可创建一条新的转换规则！'
      },
      {
        targetSelector: '#mapping-datasource-selector',
        title: '数据通道筛选',
        content: '如果映射规则过多，您可以在此筛选不同的数据来源（如通联、美团、抖音），单独查看和管理各渠道 of 字段绑定现状。'
      },
      {
        targetSelector: '#mapping-list-card',
        title: '已配置映射规则列表',
        content: '在此指定 Excel 文件中的原始列头对应系统内的标准字段，以实现对不同表格式的兼容读取。支持一键‘删除’已失效的字段映射配置。'
      }
    ];
  }
  
  isTourActive.value = true;
};

export const closeTour = () => {
  isTourActive.value = false;
  activePageTour.value = null;
};
