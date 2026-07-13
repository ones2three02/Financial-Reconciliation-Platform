# API 规范 (API.md)

## 请求与响应设计
* API 遵循 RESTful 风格。
* 所有数据接口统一返回格式为 JSON：
```json
{
  "code": 200,
  "message": "success",
  "data": { ... }
}
```
* 统一异常格式：非 2xx 请求统一返回 HTTP 异常，格式为 `{"detail": "错误详情说明"}`。
* 时间格式：接口交互统一采用 ISO 8601 标准，例如：`YYYY-MM-DDTHH:MM:SSZ`。日期字段采用 `YYYY-MM-DD`。