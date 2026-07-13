# 门店映射规范 (STORE.md)

## 门店标准化规则

1. **别名防死锁**：系统中进行账目汇总与对账计算时，**绝对禁止直接使用 Excel 原始的门店名称字符串**。必须且只能使用 mapped 绑定的标准门店名称（`standard_store_name`）。
2. **未知别名捕获**：当清洗引擎检测到未在 `store_alias` 中记录的店名时，必须自动在 `store_alias` 表中插入一条待处理别名记录，状态标为 `pending`。
3. **拦截轧账**：只要包含 `pending` 状态别名的数据行，其 clean_status 必须置为 `pending_store_mapping`，该门店当天的对账结果 status 自动标为 `missing_data`，提醒用户补全映射。