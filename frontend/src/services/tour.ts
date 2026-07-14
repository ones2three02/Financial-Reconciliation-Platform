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
        content: '在此处切换当前核对的账期日期。全平台所有数据（看板、对账单、文件明细）都会根据此日期进行自动联动切换。'
      },
      {
        targetSelector: '#dashboard-trends-card',
        title: '对账趋势与整月日历',
        content: '查看近期的对账趋势，您也可以切换到日历模式，日历中每天的格子都会用颜色直观展示当天的对账状态（已关账/待处理/存在异常）。'
      },
      {
        targetSelector: '#dashboard-discrepancy-stores',
        title: '异常门店 Top 5 榜单',
        content: '此处列出了今天对账中发生金额差异最大的前 5 家门店，点击右侧的‘去核实’可以直接跳到对账中心定位处理。'
      }
    ];
  } else if (page === 'reconciliation') {
    tourSteps.value = [
      {
        targetSelector: '#workflow-guide',
        title: '今日对账向导步骤',
        content: '这是指引您进行对账的步骤指示器。当有未匹配别名或缺失数据时，各步骤会以红色或橙色高亮发出警示。'
      },
      {
        targetSelector: '#issues-tab-btn',
        title: '1. 待人工确认门店',
        content: '此页签列出 Excel 中包含但标准店名库中未匹配的新渠道店名，需要管理员手动指定映射关联到标准店名。'
      },
      {
        targetSelector: '#integrity-tab-btn',
        title: '2. 数据来源完整性',
        content: '在此核对缺失账单数据的渠道。如果是门店当天闭店无数据，管理员可点击‘确认零收入’以便继续对账。'
      },
      {
        targetSelector: '#results-tab-btn',
        title: '3. 对账差异结果',
        content: '展示对账的最终盈亏结果明细。如果有差异，可点击‘处理差异’记录核实原因说明。'
      },
      {
        targetSelector: '#reconciliation-sidebar-actions',
        title: '对账与关账动作栏',
        content: '当数据完整后，点击‘执行对账’计算结果。核对差异并填写核实说明后，点击‘确认关账’锁定今日账期。'
      }
    ];
  } else if (page === 'import') {
    tourSteps.value = [
      {
        targetSelector: '#import-template-card',
        title: '1. 选择工作簿模板',
        content: '第一步：在此处选择需要导入的账单模板（如门店财务表、通联、美团、抖音等）。系统会根据所选模板的版本规则精确读取表头，拒绝猜测。'
      },
      {
        targetSelector: '#import-file-card',
        title: '2. 选择并导入文件',
        content: '第二步：选择好对应模板后，将交易 Excel 账单拖入此虚线框内或点击上传。系统会自动预检，确保表头和格式正确无误后，即可批量导入。'
      },
      {
        targetSelector: '#import-history-card',
        title: '当前批次导入记录',
        content: '第三步：这里展示当日批次下所有已导入的各渠道数据源文件。如果发现上传错误，支持点击“替换文件”或“作废文件”来进行冲正。'
      }
    ];
  } else if (page === 'stores') {
    tourSteps.value = [
      {
        targetSelector: '#store-tab-controls',
        title: '门店管理页签切换',
        content: '可在“标准门店管理”（维护官方店名列表）和“别名名称绑定”（管理渠道映射关联）之间进行切换。'
      },
      {
        targetSelector: '#store-list-card',
        title: '标准门店名录',
        content: '维护集团所有的标准门店信息，支持新增门店、修改区域电话，以及一键停用/启用某家门店。'
      },
      {
        targetSelector: '#store-alias-card',
        title: '渠道别名映射库',
        content: '这里记录了三方账单中的“渠道原始名称”与官方“标准店名”的绑定关系，是自动对账的核心依据。'
      }
    ];
  } else if (page === 'mappings') {
    tourSteps.value = [
      {
        targetSelector: '#mapping-datasource-selector',
        title: '配置渠道切换',
        content: '选择要配置哪一个账单来源（如通联、美团、抖音）的映射规则。'
      },
      {
        targetSelector: '#mapping-list-card',
        title: '字段映射规则表',
        content: '在此指定 Excel 文件中的原始列头（如“交易时间”）对应系统内的标准字段，以实现对不同表格式的兼容读取。'
      }
    ];
  }
  
  isTourActive.value = true;
};

export const closeTour = () => {
  isTourActive.value = false;
  activePageTour.value = null;
};
