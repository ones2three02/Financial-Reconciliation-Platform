# Financial Reconciliation Platform (FRP) — 财务自动对账平台

FRP 是一个企业级财务自动对账平台。核心围绕数据流设计，旨在实现“导出 Excel -> 拖入系统 -> 一键对账”的自动化流程。

项目支持字段映射与门店别名绑定配置，当第三方平台 Excel 模板变化或新增门店别名时，**财务人员无需修改代码，仅通过前端页面配置即可平滑完成对账**。

---

## 🌟 核心功能

1. **多层数据追踪 (Four-Layer Model)**：保留 `ImportFile` -> `RawData` -> `CleanData` -> `ReconciliationResult` 四层轨迹，支持随时重算和财务审计。
2. **字段弹性映射**：支持配置不同来源的 Excel 日期、店名和金额列头名称，防止模板变动导致系统瘫痪。
3. **门店名称标准化**：系统自动识别并捕获未知店名，提供“待确认门店别名”的认领和映射绑定界面。
4. **对账计算公式**：
   $$\text{后台收入 (通联)} + \text{美团收入} + \text{抖音收入} = \text{销售收入} - \text{现金收入}$$
5. **异常中心与 Dashboard**：高亮异常门店，支持财务手动核实备注，并通过 ECharts 展示经营趋势与门店差额排行。
6. **Excel 对账导出**：一键导出标准的 Excel 对账报表。

---

## ⚙️ 环境依赖与安装启动

项目包含后端（FastAPI + SQLite/MySQL）和前端（Vue 3 + Vite + TailwindCSS）。

### 后端服务启动

1. 进入 `backend` 目录，创建并激活虚拟环境：
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   ```
2. 安装依赖项：
   ```bash
   pip install -r requirements.txt
   ```
3. 启动 FastAPI 本地开发服务器：
   ```bash
   python run.py
   ```
   * 后端 API 地址：[http://127.0.0.1:8000](http://127.0.0.1:8000)
   * 交互式文档 Swagger UI：[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 前端页面启动

1. 进入 `frontend` 目录：
   ```bash
   cd frontend
   ```
2. 安装 npm 依赖项：
   ```bash
   npm install
   ```
3. 启动 Vite 本地开发服务器：
   ```bash
   npm run dev
   ```
   * 页面地址：打开终端输出的 Vite 本地链接（一般为 [http://localhost:5173](http://localhost:5173)）。

---

## 🧪 自动化测试验证

系统已经内置了对数据清洗服务、日期/金额提取器、门店别名匹配和对账引擎计算的自动化测试。
在 `backend` 目录中，运行以下命令即可：
```bash
source venv/bin/activate
PYTHONPATH=. pytest backend/tests/
```
*(目前测试已全部通过：`4 passed`)*
