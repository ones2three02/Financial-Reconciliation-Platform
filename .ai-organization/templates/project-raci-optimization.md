# Project RACI Matrix (项目任务与责任追踪矩阵)

- **项目名称**: 财务对账平台桌面端体验与性能优化项目
- **项目 ID**: PRJ-20260717-OPT
- **项目经理**: project-manager-01 (Project Manager)
- **更新日期**: 2026-07-17

---

## 一、项目团队成员与角色映射 (Team Mapping)

| 缩写 | 姓名/ID | 角色 | 所属部门 |
| :--- | :--- | :--- | :--- |
| **PM** | project-manager-01 | Project Manager | PMO |
| **BE** | backend-engineer-01 | Backend Engineer | Engineering |
| **FE** | frontend-engineer-01 | Frontend Engineer | Engineering |
| **QA** | qa-engineer-01 | QA Engineer | QA |

---

## 二、任务分解与责任矩阵 (WBS & RACI Matrix)

用以下状态标识完成情况：`[ ]` 未启动 / `[/]` 进行中 / `[x]` 已完成。

| 任务说明 (WBS Task) | PM | BE | FE | QA | 状态 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **【配置与联调优化】** | | | | | |
| 1. 在 `tauri.conf.json` 中配置 `beforeDevCommand` 与 `beforeBuildCommand` 实现一键开发 | **A** | **C** | **R** | | `[x]` |
| **【桌面系统适配】** | | | | | |
| 2. 在 Tauri Rust 主进程 (`main.rs`) 中实现系统托盘与“关闭即隐藏”后台保活逻辑 | **A** | | **R** | **I** | `[x]` |
| **【数据库性能优化】** | | | | | |
| 3. 在 Python 后端配置 SQLite 数据库 WAL 模式，防 Windows 下锁库死锁 | **A** | **R** | | | `[x]` |
| **【前端操作便捷化】** | | | | | |
| 4. 监听 `tauri://file-drop` 实现拖拽 Excel 流水自动进入导入 Preflight 校验管道 | **A** | | **R** | | `[x]` |
| **【整体测试与验收】** | | | | | |
| 5. 执行桌面应用端构建，跑通集成与功能验收测试 | **A** | **I** | **I** | **R** | `[x]` |

- **R (Responsible)**: 执行者（具体开发的人）。
- **A (Accountable)**: 终责人（拥有批准/否决权并为结果负最终责任）。
- **C (Consulted)**: 咨询人（在任务执行前/中提供输入、反馈的专家）。
- **I (Informed)**: 知会人（任务结果达成后需同步通知的干系人）。
