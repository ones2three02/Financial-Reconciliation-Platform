import assert from 'node:assert/strict';
import test from 'node:test';

import { parentDirectory } from '../src/services/download.ts';

test('提取 Windows 文件父目录', () => {
  assert.equal(parentDirectory('C:\\Users\\finance\\对账结果.xlsx'), 'C:\\Users\\finance');
});

test('保留 Windows 盘符根目录', () => {
  assert.equal(parentDirectory('D:\\对账结果.xlsx'), 'D:\\');
});

test('提取 POSIX 文件父目录', () => {
  assert.equal(parentDirectory('/Users/finance/对账结果.xlsx'), '/Users/finance');
});

test('无父目录的文件名返回 null', () => {
  assert.equal(parentDirectory('对账结果.xlsx'), null);
});
