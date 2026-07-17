# Project RACI Matrix (项目任务与责任追踪矩阵)

- **项目名称**: [项目名称]
- **项目 ID**: [PRJ-YYYYMMDD]
- **项目经理**: [Project Manager Agent ID]
- **更新日期**: [YYYY-MM-DD]

---

## 一、项目团队成员与角色映射 (Team Mapping)

| 缩写 | 姓名/ID | 角色 | 所属部门 |
| :--- | :--- | :--- | :--- |
| **PM** | project-manager-01 | Project Manager | PMO |
| **SA** | solution-architect-01 | Solution Architect | Architecture |
| **BE** | backend-engineer-01 | Backend Engineer | Engineering |
| **FE** | frontend-engineer-01 | Frontend Engineer | Engineering |
| **QA** | qa-engineer-01 | QA Engineer | QA |
| **QR** | quality-reviewer-01 | Quality Reviewer | QA |

---

## 二、任务分解与责任矩阵 (WBS & RACI Matrix)

用以下状态标识完成情况：`[ ]` 未启动 / `[/]` 进行中 / `[x]` 已完成。

| 任务说明 (WBS Task) | PM | SA | BE | FE | QA | QR | [其他] | 状态 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **【设计阶段】** | | | | | | | | |
| 1. 解析原始需求并输出产品 PRD | **A** | **C** | **I** | **I** | **I** | | | `[ ]` |
| 2. 设计后端核心接口 API 规范书 | **I** | **A/R**| **C** | **C** | **I** | **C** | | `[ ]` |
| 3. 设计数据库表 Schema ER 图 | | **C** | **R** | | | **A** | | `[ ]` |
| **【开发阶段】** | | | | | | | | |
| 4. 后端核心算薪与打卡逻辑编码 | **I** | **C** | **A/R**| | | **I** | | `[ ]` |
| 5. 前端交互页面与接口对接开发 | **I** | | **A/R**| | **I** | | `[ ]` |
| **【质量保障】** | | | | | | | | |
| 6. 执行后端代码 Lint 静态审计 | | | **I** | | | **A/R**| | `[ ]` |
| 7. 编写单元测试并执行覆盖率校验 | **I** | | **R** | **R** | | **A** | | `[ ]` |
| 8. 编写并运行自动化集成测试 | **A** | | **I** | **I** | **R** | | | `[ ]` |
| **【部署上线】** | | | | | | | | |
| 9. CI/CD 流水线容器部署与发布 | **A** | **I** | | | | | **R** (DevOps)| `[ ]` |

- **R (Responsible)**: 执行者（具体搬砖的人）。
- **A (Accountable)**: 终责人（拥有批准/否决权并为结果负最终责任）。
- **C (Consulted)**: 咨询人（在任务执行前/中提供输入、反馈的专家）。
- **I (Informed)**: 知会人（任务结果达成后需同步通知的干系人）。
