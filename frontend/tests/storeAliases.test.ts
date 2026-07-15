import assert from 'node:assert/strict';
import test from 'node:test';

import {
  canConfirmStoreAlias,
  findAliasForIssue,
  loadAllStoreAliases,
} from '../src/services/storeAliases.ts';

type Alias = { id: number; source_code: string; alias_name: string };

test('门店别名按服务端分页上限加载全部记录', async () => {
  const aliases = Array.from({ length: 401 }, (_, index) => ({
    id: index + 1,
    source_code: 'meituan',
    alias_name: `别名${index + 1}`,
  }));
  const requests: Array<{ skip: number; limit: number }> = [];

  const result = await loadAllStoreAliases(async (skip, limit) => {
    requests.push({ skip, limit });
    return aliases.slice(skip, skip + limit);
  });

  assert.equal(result.length, 401);
  assert.deepEqual(requests, [
    { skip: 0, limit: 200 },
    { skip: 200, limit: 200 },
    { skip: 400, limit: 200 },
  ]);
});

test('质量问题通过来源和原始门店名解析真实别名 ID', () => {
  const aliases: Alias[] = [
    { id: 17, source_code: 'meituan', alias_name: '民院门店' },
    { id: 29, source_code: 'douyin', alias_name: '民院门店' },
  ];

  assert.equal(
    findAliasForIssue(aliases, {
      id: 999,
      source_code: 'meituan',
      raw_value: '民院门店',
    })?.id,
    17,
  );
});

test('只有管理员可以确认门店别名', () => {
  assert.equal(canConfirmStoreAlias('admin'), true);
  assert.equal(canConfirmStoreAlias('finance'), false);
  assert.equal(canConfirmStoreAlias('viewer'), false);
  assert.equal(canConfirmStoreAlias(null), false);
});
