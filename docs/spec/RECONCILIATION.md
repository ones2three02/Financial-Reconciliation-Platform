# 对账引擎规范 (RECONCILIATION.md)

## 对账引擎算法

1. **公式核对**：
   * 应收预期金额（Expected Amount）：
     $$	ext{Expected} = 	ext{通联汇总} + 	ext{美团汇总} + 	ext{抖音汇总}$$
   * 实际销售金额（Actual Amount）：
     $$	ext{Actual} = 	ext{销售系统汇总} - 	ext{交班现金汇总}$$
   * 偏差值（Difference）：
     $$	ext{Difference} = 	ext{Expected} - 	ext{Actual}$$
     
2. **状态判定**：
   * 如果 $	ext{Difference} = 0$，对账状态为 `consistent` (一致)。
   * 如果其中任何一部分汇总为 0（如未上传销售 Excel），且偏差值不为 0，对账状态为 `missing_data` (缺失数据)。
   * 否则，对账状态为 `discrepancy` (异常差异)。