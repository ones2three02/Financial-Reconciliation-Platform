# Windows 桌面更新发布手册

## 能力启用说明

`v1.0.9` 是首个带应用内更新能力的引导版本候选。已经安装 `v1.0.8` 或更早版本的用户，需要手动下载并直接运行一次 `v1.0.9` NSIS 安装包进行覆盖安装，不需要先卸载，也不要删除应用数据目录。

从下一个版本开始，用户可以在左侧“桌面应用 → 检查更新”中完成更新。应用启动和登录不会自动检查。

## 签名密钥保管

- 本机加密私钥固定存放在 `$HOME/.config/frp/updater.key`，目录权限为 `700`，文件权限为 `600`。
- 公钥位于 `$HOME/.config/frp/updater.key.pub`，完整内容写入 `frontend/src-tauri/tauri.conf.json`。
- GitHub Actions 只使用 `TAURI_PRIVATE_KEY` 和 `TAURI_KEY_PASSWORD` 两个 Repository Secret。
- 私钥和密码必须另存到密码管理器或离线安全介质，不得写入仓库、聊天、Issue、Release、构建日志或普通文档。
- `gh secret list` 只能确认 Secret 名称存在，禁止尝试读取或打印 Secret 值。
- 私钥丢失后，现有客户端无法验证由新密钥签名的更新。此时不得静默替换公钥，必须发布一个新的手动覆盖引导版本。

## 发布前检查

1. 确认工作分支为 `feature/desktop-tauri`，不得从 `main` 发布桌面版本。
2. 更新 `frontend/src-tauri/tauri.conf.json` 中的 `package.version`。
3. 版本必须严格递增且采用 `MAJOR.MINOR.PATCH`；标签必须为对应的 `vMAJOR.MINOR.PATCH`。
4. 执行后端全量测试、前端测试与构建、Rust 测试和 clippy。
5. 确认 `git diff --check` 通过，工作区不包含私钥、密码、数据库或本地构建产物。
6. 使用版本校验脚本验证标签与配置一致：

```bash
venv/bin/python backend/scripts/verify_desktop_version.py v1.0.9 frontend/src-tauri/tauri.conf.json
```

## 发布流程

只有在用户明确授权提交、推送和发布后才能执行：

1. 提交桌面版本改动并推送 `feature/desktop-tauri`。
2. 在同一提交创建版本标签并推送标签；禁止 force-push，禁止复用失败标签覆盖旧产物。
3. GitHub Actions 使用签名 Secret 构建 Windows NSIS 安装包和更新归档。
4. 等待 `publish-tauri` 与 `verify-updater-release` 全部成功。
5. 工作流失败时保留现场排查，不自动删除 Release，也不把失败发布通知给用户使用。

## Release 产物验收

每个支持应用内更新的 Release 必须同时包含：

- 普通 Windows NSIS `.exe` 安装包；
- `.nsis.zip` 更新归档；
- 更新归档对应的 `.sig` 文件；
- `latest.json`。

`latest.json` 必须包含 `windows-x86_64`，URL 必须指向当前标签下的 `.nsis.zip`，signature 必须非空。可以下载后本地复核：

```bash
venv/bin/python backend/scripts/verify_updater_manifest.py latest.json v1.0.9
```

脚本只打印版本与下载地址，不打印签名内容。

## Windows 引导版本验收

1. 在干净 Windows 环境安装旧版本，创建测试账号和一批可辨识的本地数据。
2. 不卸载旧版本，直接运行引导版本 NSIS 安装包覆盖安装。
3. 确认应用标识和安装位置未产生第二份程序。
4. 启动后确认账号、门店、字段映射、批次、导入记录和 SQLite 数据保留。
5. 确认 Python sidecar 能启动，登录和 Excel 导入正常。
6. 左侧显示“桌面应用 → 检查更新 · v当前版本”；启动时没有自动更新提示。
7. 点击检查更新，引导版本作为最新版本时应提示“当前已是最新版本”。

## 应用内更新闭环验收

1. 发布一个更高版本，Release Notes 写入可辨识的测试说明。
2. 在旧版应用中手动点击“检查更新”。
3. 核对当前版本、新版本、发布日期和发布说明。
4. 点击“下载并安装”，确认下载进度、签名校验和 NSIS 被动安装执行。
5. 确认应用自动重启，版本号已更新。
6. 重启后确认登录、sidecar、数据库迁移和既有业务数据正常。
7. 使用隔离的错误签名测试清单验证客户端拒绝安装，且旧版仍能运行。错误签名测试不得污染正式 `latest.json`。

## 故障处理

- GitHub 不可达：本地对账不受影响，恢复网络后重新检查。
- `latest.json` 缺失或格式错误：停止通知用户升级，修复发布流水线并使用新版本号重新发布。
- 签名验证失败：绝不提供跳过校验选项，检查私钥、公钥和 Release 归档是否属于同一次构建。
- 安装失败：保留现有版本和数据库，关闭占用程序后重试；必要时下载普通 NSIS 包手动覆盖安装。
- 密钥丢失：停止应用内更新发布，制作带新公钥的手动覆盖引导版本，并明确通知用户安装一次。
