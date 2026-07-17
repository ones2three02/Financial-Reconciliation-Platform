# AI Organization Escalation Policy (升级与人机协作政策)

本规范规定了 Agent 在何种条件下必须将决策或问题“升级”（Escalate）至人类专家（Human Expert），以及升级过程中的标准交互流程。

## 第一章 升级触发场景 (Escalation Triggers)

当 Agent 在工作流中遇到以下任意场景时，必须立即终止自主执行，触发升级流程：

1. **红线与合规决策**：
   - 涉及商业法律法规、行业合规（如 GDPR 隐私合规、医疗健康合规）的评估。
   - 需要修改全局的 `core/organization-policy.md`。
2. **敏感财务或资源支出**：
   - 涉及需要调用付费第三方 API，或涉及虚拟企业本身的财务交易、资源买卖决策。
3. **不可调和的死锁冲突**：
   - 两个及以上 L2 级（如 Solution Architect 与 Project Manager）在方案设计上产生死锁冲突，且依据 `core/decision-policy.md` 无法通过委员会多数决达成一致。
4. **越权及核心信息缺失**：
   - 无法从现有项目上下文中推断出关键需求，且向产品经理/上级求助依然无法解决。

---

## 第二章 升级文件规范 (Human Decision Required)

触发升级后，当前负责 of Agent 必须在其工作目录或任务日志中生成一份标准的升级审批单，其模板格式如下：

```markdown
# ⚠️ HUMAN DECISION REQUIRED (人类决策审批单)

- **发起 Agent**: [Agent ID, 如 pmo-project-manager-01]
- **关联项目**: [项目名称 / ID]
- **严重等级**: [High / Medium]

### 一、当前问题描述 (Problem Statement)
[清晰明了地用一句话说明遇到了什么阻碍、冲突或红线问题]

### 二、背景与上下文 (Context)
[提供必要的背景信息，包括冲突的起因、缺失的条件或面临的法律条款]

### 三、可能带来的潜在影响 (Impact Analysis)
- **如果通过**: [描述对项目进度、质量或成本的积极/消极影响]
- **如果拒绝**: [描述拒绝后可能导致的后果]

### 四、推荐解决方案 (Recommendation)
[发起 Agent 或决策小组讨论后推荐的首选方案，以及推荐理由]

### 五、需要人类确认的事项 (Actions Required)
1. 请确认：[具体需要人类做出的单选、多选或文本确认]
```

---

## 第三章 任务挂起与恢复流程 (Pending & Resume)

1. **进入 PENDING 状态**：
   - 发起 Agent 生成“人类决策审批单”后，应将自身和受影响任务的状态标记为 `PENDING_HUMAN_APPROVAL`。
   - 停止执行所有可能产生副作用的代码修改或系统操作，释放非必要 system 锁。
2. **人类答复解析**：
   - 当人类在审批单中填写了确认意见，或在对话框中给出了明确指令后，系统将读取该信息。
3. **状态恢复 (Resume)**：
   - Organization Manager 校验人类决策记录，确认签字（Signature）或批准指令有效。
   - 解锁挂起的任务，将人类决定作为高优先级上下文输入给相关 Agent，Agent 更新项目文档后继续执行。
