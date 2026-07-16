import assert from 'node:assert/strict';
import test from 'node:test';

import {
  FIELD_MAPPING_SOURCES,
  targetFieldOptionsForSource,
} from '../src/services/fieldMappingOptions.ts';


test('字段映射只展示四个真实输入来源', () => {
  assert.deepEqual(
    FIELD_MAPPING_SOURCES.map((source) => source.value),
    ['tonglian', 'meituan', 'douyin', 'store_finance'],
  );
});


test('每个来源只允许模板实际使用的标准字段', () => {
  assert.deepEqual(
    targetFieldOptionsForSource('tonglian').map((field) => field.value),
    ['trade_date', 'store_name', 'amount'],
  );
  assert.deepEqual(
    targetFieldOptionsForSource('meituan').map((field) => field.value),
    ['trade_date', 'store_name', 'amount', 'marketing_fee'],
  );
  assert.deepEqual(
    targetFieldOptionsForSource('store_finance').map((field) => field.value),
    ['trade_date', 'amount', 'payment_method'],
  );
});


test('未知来源不返回可选标准字段', () => {
  assert.deepEqual(targetFieldOptionsForSource('cash'), []);
});
