# AI Organization Operating System v1.0 (AI Org OS)

AI Organization OS 是一套运行在 AI 编程助手（如 Codex）之上的虚拟 AI 企业操作系统。通过这套系统，AI 不再只是一个被动接收指令的工具，而是能够自主理解业务需求、评估自身能力缺口、启动招聘流程、组建多 Agent 项目团队并进行人机协作的“虚拟 AI 企业”。

## 💡 核心设计理念

1. **Agent 是组织成员**：每个 Agent 必须具备明确的组织身份、岗位职责、能力边界与汇报线。
2. **组织化协同**：复杂企业任务禁止单 Agent 独立完成，必须通过 RACI 矩阵组织化、多角色协同执行。
3. **能力动态扩展**：当项目需要特定能力，而注册中心（Registry）中无匹配 Agent 时，自动触发 AI 招聘流程，从岗位分析、JD 生成、候选人面试到最终录用注册，全部由 AI HR 模块自主完成。
4. **安全升级与人机协作**：当涉及企业红线、高风险决策或信息不足时，通过 `human-escalation` 机制挂起任务，生成标准的人类确认单，等待真人审批。

---

## 📂 目录结构

```
.ai-organization/
├── README.md                           # 本指南文件
├── core/                               # 核心政策与运行规则
│   ├── organization-policy.md          # 组织第一原则（人机边界、基本假设）
│   ├── operating-rules.md              # 运行基本规则与信息流转规范
│   ├── agent-lifecycle.md              # Agent 生命周期管理（从招聘到离职）
│   ├── decision-policy.md              # 决策流与授权层级
│   └── escalation-policy.md            # 升级与人类介入规则
├── registry/                           # 注册中心
│   ├── agent-registry.yaml             # 活跃 Agent 实例名单
│   ├── capability-registry.yaml        # 能力矩阵定义
│   └── role-registry.yaml              # 标准岗位定义
├── organization/                       # 组织架构
│   ├── structure.yaml                  # 组织树状层级
│   └── departments.yaml                # 部门职责范围
├── agents/                             # 岗位定义（System Prompts）
│   ├── executive/                      # 管理层（CEO, Organization Manager）
│   ├── hr/                             # 人力资源部（HR Manager, Recruiter, Onboarding, etc.）
│   ├── pmo/                            # 项目管理部（Project Manager, Product Manager）
│   ├── architecture/                   # 架构部（Solution, Database, Security）
│   ├── engineering/                    # 工程部（Backend, Frontend, DevOps）
│   ├── quality/                        # 质量保障部（QA, Reviewer）
│   └── domain/                         # 领域专家池（HR, Finance, Legal Experts）
├── skills/                             # 行为规范与操作手册（Codex 技能包）
└── templates/                          # 流程模版与标准产物
```

---

## 🚀 模拟运行场景：开发企业人力系统 (Enterprise HR System)

为了让 Codex / AI 助手体验此操作系统的魅力，请复制以下引导提示词并发送给 AI，启动虚拟 AI 公司的运行：

### 🛠️ 模拟引导提示词 (Simulation Prompt)

> **[系统指令]**
> 请加载当前工作区中 `.ai-organization/` 的所有配置、岗位定义与 Skills。
> 现在，我们将模拟启动一个名为 **“开发企业人力系统（Enterprise HR System）”** 的项目。
> 
> **用户输入**：
> “公司决定研发一套全新的企业人力系统。该系统需要具备员工信息管理、出勤打卡、薪酬发放与年假审批功能。请立即启动项目。”
> 
> **执行要求**：
> 1. 请作为 **Organization Manager Agent** 启动。
> 2. 阅读 `core/organization-policy.md` 与 `skills/organization-manager/SKILL.md`。
> 3. 对项目进行需求分析与能力矩阵匹配，并在 `registry/agent-registry.yaml` 中查找匹配的 Agent。
> 4. 若发现缺少 **Payroll Expert（薪酬发放专家）** 等关键岗位，暂停项目执行，立即流转给 **AI HR Manager** 启动招聘流程。
> 5. 按照 `skills/recruitment/SKILL.md` 与 `skills/interview/SKILL.md` 模拟完成：
>    - 生成 `templates/job-request.md` 并转换为招聘 JD。
>    - 模拟面试 3 个候选 Agent，打分并产出 `templates/interview-report.md`。
>    - 选择最优候选人，更新 `registry/agent-registry.yaml`。
>    - 模拟新 Agent 执行 Onboarding 培训。
> 6. 重新组建团队，生成 `templates/project-raci.md`。
> 7. 在执行到“年假审批与公司年假规则”相关设计时，触发 `skills/human-escalation/SKILL.md`，向人类提出审批。
