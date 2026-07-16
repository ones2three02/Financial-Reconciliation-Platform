export type FieldMappingTarget =
  | 'trade_date'
  | 'store_name'
  | 'amount'
  | 'marketing_fee'
  | 'payment_method';

export interface FieldMappingTargetOption {
  value: FieldMappingTarget;
  label: string;
}

export interface FieldMappingSourceOption {
  value: string;
  label: string;
  badge: string;
  targets: FieldMappingTargetOption[];
}

const commonTargets = {
  tradeDate: { value: 'trade_date', label: '交易日期 (trade_date)' },
  storeName: { value: 'store_name', label: '门店名称 (store_name)' },
  amount: { value: 'amount', label: '主金额 (amount)' },
  marketingFee: { value: 'marketing_fee', label: '商家营销费用 (marketing_fee)' },
  paymentMethod: { value: 'payment_method', label: '付款方式 (payment_method)' },
} satisfies Record<string, FieldMappingTargetOption>;

export const FIELD_MAPPING_SOURCES: FieldMappingSourceOption[] = [
  {
    value: 'tonglian',
    label: '通联后台',
    badge: 'bg-violet-50 text-violet-600',
    targets: [commonTargets.tradeDate, commonTargets.storeName, commonTargets.amount],
  },
  {
    value: 'meituan',
    label: '美团收入',
    badge: 'bg-amber-50 text-amber-600',
    targets: [
      commonTargets.tradeDate,
      commonTargets.storeName,
      commonTargets.amount,
      commonTargets.marketingFee,
    ],
  },
  {
    value: 'douyin',
    label: '抖音收入',
    badge: 'bg-slate-100 text-slate-700',
    targets: [commonTargets.tradeDate, commonTargets.storeName, commonTargets.amount],
  },
  {
    value: 'store_finance',
    label: '门店财务表',
    badge: 'bg-blue-50 text-blue-600',
    targets: [commonTargets.tradeDate, commonTargets.amount, commonTargets.paymentMethod],
  },
];

export const targetFieldOptionsForSource = (
  source: string,
): FieldMappingTargetOption[] => (
  FIELD_MAPPING_SOURCES.find((item) => item.value === source)?.targets ?? []
);

export const targetFieldLabel = (target: string): string => {
  for (const source of FIELD_MAPPING_SOURCES) {
    const option = source.targets.find((item) => item.value === target);
    if (option) return option.label;
  }
  return target;
};
