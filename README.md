# Financial Reconciliation Platform (FRP) — 财务自动对账平台

FRP 是一个企业级财务自动对账平台。核心围绕数据流设计，旨在实现“导出 Excel -> 拖入系统 -> 一键对账”的自动化流程。

当前版本使用有版本号的白名单提取模板处理第三方 Excel。新增门店别名必须由财务人员人工确认，系统不会根据相似名称自行绑定。

---

## 🌟 核心功能

1. **全链路追踪**：保留批次、导入文件、原始数据、提取运行、标准数据、来源完整性和对账结果，支持重算和审计。
2. **模板预检**：在持久化前校验工作表、表头、业务日期、文件规模和模板版本，模板不匹配时拒绝导入。
3. **门店名称标准化**：未知店名进入待确认池，只有人工确认后的“来源 + 别名”映射才能参与对账。
4. **对账计算公式**：
   $$\text{后台收入 (通联)} + \text{美团收入} + \text{抖音收入} = \text{销售收入} - \text{现金收入}$$
5. **完整性门禁**：明确区分零收入和缺少数据；缺失来源、待确认门店或解析错误均不能关账。
6. **单人关账**：不设置经办/复核双人审批；关账和带原因重开均写入审计事件。

---

## ⚙️ 环境依赖与安装启动

项目包含后端（FastAPI + SQLite/MySQL）和前端（Vue 3 + Vite + TailwindCSS）。

### 后端服务启动

1. 复制本地配置并按环境修改，配置文件不得提交到仓库：
   ```bash
   cp backend/.env.example backend/.env
   ```
2. 在项目根目录创建并激活虚拟环境：
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. 安装依赖项：
   ```bash
   pip install -r backend/requirements.txt
   ```
4. 创建或升级数据库结构：
   ```bash
   alembic -c backend/alembic.ini upgrade head
   ```
5. 显式初始化门店，并通过交互式命令创建第一个管理员。系统不提供默认账户或默认密码：
   ```bash
   python -m backend.scripts.seed_stores
   python -m backend.scripts.create_admin <管理员用户名>
   ```
6. 启动 FastAPI 本地开发服务器：
   ```bash
   python backend/run.py
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
   * 开发服务器默认将 `/api` 转发到 `http://127.0.0.1:8000`；部署时也推荐由同源反向代理转发。
   * 如需使用独立 API 地址，可通过 `VITE_API_BASE_URL` 指定完整的 `/api/v1` 基础地址。

### 每日使用顺序

1. 在顶部选择账期，到“文件导入”创建或载入当日批次；
2. 按模板批量选择文件：门店财务表、通联、美团、抖音；
3. 每份文件先预检再导入，其中门店财务表一次生成销售收入和现金收入；
4. 到“对账明细”处理待确认门店，未知名称必须由管理员选择标准门店；
5. 对真实零收入来源执行“确认零收入”，不要用缺失代替零；
6. 执行对账，处理金额差异并填写核实说明；
7. 批次显示“可关账”后由财务单人关账；如需修改，填写原因重开。

---

## 🧪 自动化测试验证

系统已经内置了对数据清洗服务、日期/金额提取器、门店别名匹配和对账引擎计算的自动化测试。
在项目根目录中，运行以下命令：
```bash
PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -p no:cacheprovider backend/tests -q
```

数据库迁移与备份步骤见 [docs/database/migration.md](docs/database/migration.md)。
