# 数据库数据字典 (dictionary.md)

FRP MVP 数据库核心表字段设计如下：

### 1. 导入文件表 `import_file`
* `id`: INT, 自增主键
* `filename`: VARCHAR(255), 上传文件名
* `data_source`: VARCHAR(50), 来源渠道（tonglian, meituan, douyin, cash, sales）
* `upload_status`: VARCHAR(20), 上传状态（pending, parsed, failed）
* `error_message`: TEXT, 失败错误描述
* `row_count`: INT, 解析出的原始记录行数
* `uploaded_at`: DATETIME, 上传时间

### 2. 标准门店表 `store`
* `id`: INT, 自增主键
* `name`: VARCHAR(100), 标准门店名
* `is_active`: TINYINT(1), 是否启用
* `created_at`: DATETIME, 创建时间

### 3. 门店别名表 `store_alias`
* `id`: INT, 自增主键
* `alias_name`: VARCHAR(100), Excel中出现的原始门店名
* `store_id`: INT, 关联的标准门店主键ID (FK)
* `status`: VARCHAR(20), 绑定状态 (mapped, pending)