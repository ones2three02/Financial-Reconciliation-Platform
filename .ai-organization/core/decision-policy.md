# AI Organization Decision & Approval Policy (决策与审批政策)

本规范规定了虚拟企业内部的决策链条、授权等级和多 Agent 协同审批流程。

## 第一章 决策授权层级 (Authority Levels)

本系统将决策权限划分为四个层级，以平衡决策效率与系统安全性：

| 授权等级 | 决策范围 | 审批主体 | 流程要求 |
| :--- | :--- | :--- | :--- |
| **L4: 战略级** | 企业政策修改、重大预算审批、真人人机协作决策 | **人类专家 (Human Expert)** | 必须通过 `human-escalation` 触发，人类签署确认单。 |
| **L3: 组织级** | 组织结构调整、跨部门纠纷仲裁、部门负责人任命 | **CEO Agent** | 听取各部门汇报后，CEO Agent 做出最终单向决定，并归档记录。 |
| **L2: 项目/技术级**| 架构设计、数据库变更、项目交付、新增岗位录用 | **PMO / Tech Lead / HR Manager** | 相关负责人决策，需有一位同级/上级 Agent 会签（Co-sign）。 |
| **L1: 执行级** | 单个文件编写、单元测试执行、日常代码重构 | **执行层 Agent (Backend/Frontend/QA)** | 依据 JD 自主决定，并在运行日志中写明 Rationale。 |

---

## 第二章 重大决策审批流 (Approval Workflow)

### 2.1 技术架构与数据库设计审批
1. **方案提交**：Solution Architect 或 Database Architect 完成设计，生成 `templates/decision-record.md` 提案。
2. **多方会签**：
   - Project Manager 审核进度与成本影响（签署：Approve/Reject）。
   - Security Architect 审核安全性（签署：Approve/Reject）。
3. **终审**：所有会签人同意后，提交给 Organization Manager 批准并启动执行。

### 2.2 岗位录用审批
1. **面试打分**：Interviewer Agent 完成面试并生成报告。
2. **编制核对**：AI HR Manager 核对是否超出部门编制预算。
3. **录用生效**：HR Manager 签署同意，并将报告抄送 CEO Agent 归档，交由 Onboarding Agent 执行入职。

---

## 第三章 会签与多数决共识机制 (Consensus Mechanism)

当出现复杂的技术路线分歧，或无明确责任人时，应触发“多数决共识”：
- **委员会组建**：由 Organization Manager 召集与议题相关的 3 个或 5 个奇数个 Agent（如 Solution Architect, Quality Reviewer, DevOps Engineer 等）组成临时决策小组。
- **投票表决**：各小组成员评估提案并进行投票。必须获得 **超过半数（>50%）** 的赞成票，提案才能通过。
- **记录归档**：投票结果及各方立场必须完整写入 `templates/decision-record.md`。
