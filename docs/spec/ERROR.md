# 错误处理规范 (ERROR.md)

## 全局异常捕捉规则
* 后端使用 FastAPI 的 `HTTPException` 进行业务级别阻断。
* 数据库操作异常、Excel 文件解析格式损坏，统一在 Service 层进行 try-except 封装，并将报错转换为友好的中文提示信息抛给前端，防止将原始 Python 报错堆栈直接暴露在 UI 界面。