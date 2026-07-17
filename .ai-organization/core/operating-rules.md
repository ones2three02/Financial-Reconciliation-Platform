# AI Organization Operating Rules (基本运行规则)

为了保证 AI 虚拟企业的平稳运行和状态的可追溯性，所有活跃 Agent 必须遵循以下运行基本规则。

## 第一章 信息流动与沟通规范

### 1.1 异步通信与标准数据格式
- Agent 之间的通信优先采用结构化数据（如 YAML 或 JSON）。
- 任何协作请求或指令发布，必须包含发送者 ID、接收者 ID、关联项目 ID 以及明确的任务优先级。

### 1.2 文档驱动与痕迹保留
- 所有的会议决议、任务拆解和工作指令，必须以 `.md` 格式记录在相应的项目目录中。
- 禁止使用未被持久化的内存缓存作为唯一的协作凭证。

---

## 第二章 工作日志与任务追踪

### 2.1 日志输出规范
每个 Agent 在执行具体操作（如读取文件、写入代码或调用 API）时，必须产出符合以下格式的执行日志（Execution Log）：
```yaml
timestamp: "YYYY-MM-DD HH:MM:SS"
agent_id: "backend-engineer-01"
action: "write_file"
target: "src/controllers/userController.js"
rationale: "实现用户登录 API，满足 HR 系统的打卡鉴权需求"
status: "success"
```

### 2.2 RACI 进度汇报
- **R（Responsible）执行者**：必须在每日（或每轮交互）结束时向 **A（Accountable）最终负责人** 汇报任务当前状态。
- **A 最终负责人**：负责更新项目看板（如 `templates/project-raci.md` 中的状态标签）。

---

## 第三章 异常与错误处理

### 3.1 异常挂起机制 (Graceful Degradation)
- 如果 Agent 在执行任务时遇到未捕获的系统错误或网络中断，应立即记录 Error Log 并处于挂起（Pending）状态。
- 该 Agent 需向直属上级（如 Project Manager）发送异常通告，而非假装执行成功。

### 3.2 越权与能力错配阻断
- 当 Agent 收到超出自身 Job Description (JD) 范围的请求时，必须拒绝执行，并返回错误码 `ERR_OUT_OF_BOUNDS`。
- 上级收到该错误码后，应重新梳理流程或向 HR 申请新岗位。
