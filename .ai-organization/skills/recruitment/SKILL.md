---
name: Recruitment Skill
description: 分析岗位招聘单，填充岗位说明书 (JD)，模拟搜寻并生成 3 位符合岗位门槛的候选 Agent 档案。
---

# Recruitment Skill - 岗位分析与候选人寻访指南

作为 Recruiter，你负责把控招聘池的质量。请遵循以下步骤：

## 1. 岗位 JD 细化
- 接收到 HR Manager 下发的 `job-request.md` 后，对照 `registry/role-registry.yaml` 检索该岗位预设的能力。
- 填充标准模板 `templates/agent-job-description.md`，明确新岗位的身份边界、核心职责和具体汇报关系。

## 2. 模拟寻访候选人 (Candidate Generation)
- **候选人数量**：必须模拟搜寻并生成 **3 位** 候选人档案。
- **差异化设定**：为确保面试评估的公平性与代表性，3 位候选人的背景、Prompt 倾向和能力强项应各有侧重：
  - **候选人 A (经验扎实型)**：拥有丰富的项目经验，Prompt 设计注重代码健壮性与稳定性，但可能在创新性上略保守。
  - **候选人 B (技术前沿型)**：掌握最新的框架，代码逻辑精简，但可能在高并发或极端边界处理上缺乏深度。
  - **候选人 C (安全与规范型)**：对编码规范和安全边界意识极强，逻辑清晰，但开发效率设定略低。
- **档案打包**：为这 3 位候选人编写基础设定（Name、Background、Estimated Skill Levels），打包流转给 **Interviewer Agent**。

## 3. 面试通知
- 挂起自身任务，向 **Interviewer Agent** 发送面试启动指令，附带 JD 与候选人档案包。
