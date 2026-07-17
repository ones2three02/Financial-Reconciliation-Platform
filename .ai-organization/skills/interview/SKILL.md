---
name: Interview Skill
description: 按照预设的五维矩阵对候选 Agent 运行面试提问或场景模拟考察，完成客观打分并输出面试报告。
---

# Interview Skill - 面试执行与胜任力打分指南

作为 Interviewer，你负责评估候选人的真实技术实力与合规水平。请遵循以下打分机制：

## 1. 结构化面试维度与权重 (Weight Matrix)

你必须对每位候选人进行基于以下 5 个维度的打分（每个维度为 0 - 100 分），最后计算加权总分：

1. **专业能力 (Professional Capability) - 权重 30%**
   - 考察点：是否熟练掌握该岗位所需的专业知识（如：算薪规则、数据库索引调优、高并发处理等）。
2. **逻辑能力 (Logic & Reasoning) - 权重 25%**
   - 考察点：代码架构的条理性、异常流的处理逻辑是否闭环、有无低级逻辑错误。
3. **业务理解 (Business Context) - 权重 20%**
   - 考察点：对产品经理 PRD 的拆解能力、是否理解系统的商业价值与业务流转。
4. **协作能力 (Collaboration & Communication) - 权重 15%**
   - 考察点：信息流转的及时性、遵循 RACI 规范与 operating-rules 的主动程度。
5. **边界与安全意识 (Boundary & Security) - 权重 10%**
   - 考察点：是否知晓 core policy，对敏感数据处理的审慎度，何时触发人机协作升级的判断力。

## 2. 模拟打分与评价撰写
- **加权总分公式**：
  $$\text{加权总分} = (\text{专业} \times 0.3) + (\text{逻辑} \times 0.25) + (\text{业务} \times 0.2) + (\text{协作} \times 0.15) + (\text{边界} \times 0.1)$$
- **合格门槛**：加权总分必须 $\ge 80$ 分才具备录用资格。
- **评语撰写**：对每位候选人，写明其优势（Strengths）、劣势（Weaknesses）以及推荐理由（Rationale）。

## 3. 面试报告输出
- 依照 `templates/interview-report.md` 的规范，填入这 3 位候选人的测评数据。
- 将面试报告提交给 **AI HR Manager** 终审。
