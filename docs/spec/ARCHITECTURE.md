# 架构规范 (ARCHITECTURE.md)

FRP 系统架构采用经典的 Monorepo 形式，包括前后端解耦的 Client-Server 模式。

## 目录布局
```
financial-reconciliation-platform/
├── backend/                  # FastAPI 后端服务
│   ├── app/
│   │   ├── core/             # 数据库引擎与配置
│   │   ├── models/           # ORM 实体
│   │   ├── schemas/          # Pydantic 校验 Schema
│   │   ├── crud/             # 数据库读写
│   │   ├── services/         # 核心业务逻辑(解析/清洗/对账)
│   │   └── api/              # API 路由器
│   └── tests/                # Pytest 自动化测试
└── frontend/                 # Vite + Vue3 前端应用
    ├── src/
    │   ├── services/         # API 客户端
    │   ├── views/            # 页面视图组件
    │   └── router/           # 路由配置
```

## 核心设计规范
* **动静分离**：Controller (API) 只做输入参数校验与 HTTP 状态分发，核心清洗、解析、对账算法必须下沉到 Service 层。
* **数据传递**：Service 层只处理标准类型或 Pydantic Schema，不访问 Request 报文对象。