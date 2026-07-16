# Windows 桌面端应用内更新 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Windows 桌面端增加只由用户手动触发的签名更新能力，并按已确认的 B 方案重整左侧导航、展示发布说明和安装进度。

**Architecture:** 保持 Tauri 1.x，通过内置 updater 从 GitHub Releases 的 `latest.json` 获取并校验 NSIS 更新包。前端把 Tauri 全局 API 封装在可注入、可单测的 `desktopUpdater` 服务中，再由框架无关状态控制器驱动 Vue 弹窗和侧栏入口；发布流水线使用 GitHub Secrets 签名并在发布后验证更新清单。

**Tech Stack:** Tauri 1.5、Rust 2021、Vue 3、TypeScript、Node test runner、GitHub Actions、NSIS、Python/pytest

## Global Constraints

- 只支持 Windows 桌面端；Web 版和 macOS 不显示更新入口。
- 只允许手动检查；应用启动、登录和页面切换不得调用更新检查 API。
- 所有已登录角色都能使用更新入口；管理员权限只继续约束数据配置菜单。
- 左侧导航采用“日常工作 / 数据配置 / 桌面应用”分组，更新弹窗采用已确认的 B 方案。
- 使用 Tauri 1 内置 updater 和公开 GitHub Releases，不升级到 Tauri 2，不实现自定义下载器。
- 更新包必须通过 Tauri 公钥校验，不允许跳过签名、修改 endpoint 或远程降级。
- 保持应用标识 `com.ones2three02.reconflow` 和 Windows NSIS 安装格式，确保覆盖安装而非创建第二份应用。
- 当前版本 `1.0.9` 是首个带更新器的引导版本候选；发布前不擅自创建标签或 Release。
- 继续在 `feature/desktop-tauri` 工作，不合并到 `main`。
- 未获得明确授权前不提交、不推送、不创建 GitHub Secrets、不发布 Release。

---

## 文件结构

- `frontend/src/services/desktopUpdater.ts`：Tauri 运行环境、版本、检查、安装、进度监听和错误文案适配。
- `frontend/src/services/desktopUpdaterController.ts`：框架无关的更新状态机，负责防重复和状态转换。
- `frontend/src/components/DesktopUpdater.vue`：侧栏入口与应用内更新弹窗。
- `frontend/src/App.vue`：B 版导航分组、桌面更新组件挂载和本地服务状态。
- `frontend/src/services/desktopRuntime.ts`：扩展全局 Tauri bridge 类型，供更新服务安全调用。
- `frontend/tests/desktopUpdater.test.ts`：运行环境、API 清理、进度和错误映射测试。
- `frontend/tests/desktopUpdaterController.test.ts`：手动触发、状态转换和并发门禁测试。
- `frontend/src-tauri/Cargo.toml`：启用 `updater` 与 Windows 平台识别所需 Tauri 特性。
- `frontend/src-tauri/tauri.conf.json`：GitHub endpoint、公钥、关闭默认弹窗和 Windows 被动安装。
- `backend/tests/test_desktop_updater_configuration.py`：静态校验 Tauri 和发布配置。
- `backend/scripts/verify_updater_manifest.py`：校验 Release 的 Windows 更新清单。
- `backend/tests/test_updater_manifest.py`：更新清单校验器单元测试。
- `.github/workflows/release.yml`：签名、生成 `latest.json`、优先 NSIS 和发布后验证。
- `docs/desktop/windows-update-release.md`：密钥保管、首次引导发布和 Windows 真机验收手册。

### Task 1: 封装 Windows Tauri 更新运行时

**Files:**
- Modify: `frontend/src/services/desktopRuntime.ts`
- Create: `frontend/src/services/desktopUpdater.ts`
- Create: `frontend/tests/desktopUpdater.test.ts`

**Interfaces:**
- Produces: `isWindowsDesktop(runtime: DesktopUpdaterRuntime): Promise<boolean>`。
- Produces: `getCurrentDesktopVersion(runtime: DesktopUpdaterRuntime): Promise<string>`。
- Produces: `checkForDesktopUpdate(runtime: DesktopUpdaterRuntime): Promise<DesktopUpdateCheckResult>`。
- Produces: `installDesktopUpdate(runtime, onProgress): Promise<void>`。
- Produces: `desktopUpdateErrorMessage(error: unknown): string`。
- Produces: `DesktopUpdateManifest`、`DesktopUpdateProgress`、`DesktopUpdaterRuntime` 类型；进度事件明确区分 `downloading` 和 `installing`。

- [ ] **Step 1: 写 Windows 运行时与手动检查失败测试**

创建 `frontend/tests/desktopUpdater.test.ts`，使用真实对象而不是测试框架 mock：

```ts
import assert from 'node:assert/strict';
import test from 'node:test';

import {
  checkForDesktopUpdate,
  getCurrentDesktopVersion,
  isWindowsDesktop,
} from '../src/services/desktopUpdater.ts';

const runtime = (platform: string, shouldUpdate = false) => ({
  location: { protocol: 'https:', hostname: 'tauri.localhost' },
  __TAURI__: {
    app: { getVersion: async () => '1.0.9' },
    os: { platform: async () => platform },
    updater: {
      checkUpdate: async () => shouldUpdate
        ? { shouldUpdate: true, manifest: { version: '1.0.10', date: '2026-07-17', body: '修复导入问题' } }
        : { shouldUpdate: false },
      installUpdate: async () => undefined,
      onUpdaterEvent: async () => () => undefined,
    },
    event: { listen: async () => () => undefined },
  },
});

test('只有 Windows Tauri 环境支持桌面更新', async () => {
  assert.equal(await isWindowsDesktop(runtime('win32')), true);
  assert.equal(await isWindowsDesktop(runtime('darwin')), false);
  assert.equal(await isWindowsDesktop({ location: { protocol: 'https:', hostname: 'example.com' } }), false);
});

test('读取实际运行版本且检查动作返回稳定业务结果', async () => {
  assert.equal(await getCurrentDesktopVersion(runtime('win32')), '1.0.9');
  assert.deepEqual(await checkForDesktopUpdate(runtime('win32', true)), {
    status: 'available',
    manifest: { version: '1.0.10', date: '2026-07-17', body: '修复导入问题' },
  });
});
```

- [ ] **Step 2: 运行测试并确认 RED**

Run: `cd frontend && node --test tests/desktopUpdater.test.ts`

Expected: FAIL，提示找不到 `desktopUpdater.ts`。

- [ ] **Step 3: 扩展 Tauri bridge 类型并实现最小检查能力**

在 `desktopRuntime.ts` 中把 `TauriBridge` 扩展为可选的 `app`、`os`、`updater`、`event` 模块；不要使用 `any`。在 `desktopUpdater.ts` 中：

```ts
export type DesktopUpdateCheckResult =
  | { status: 'up_to_date' }
  | { status: 'available'; manifest: DesktopUpdateManifest };

export const isWindowsDesktop = async (runtime: DesktopUpdaterRuntime) => {
  if (!isTauriRuntime(runtime) || !runtime.__TAURI__?.os) return false;
  return (await runtime.__TAURI__.os.platform()) === 'win32';
};

export const checkForDesktopUpdate = async (runtime: DesktopUpdaterRuntime) => {
  if (!(await isWindowsDesktop(runtime))) throw new Error('不支持当前运行环境');
  const updater = requireUpdater(runtime);
  const result = await updater.checkUpdate();
  if (!result.shouldUpdate) return { status: 'up_to_date' } as const;
  if (!result.manifest?.version) throw new Error('更新清单格式无效');
  return { status: 'available', manifest: normalizeManifest(result.manifest) } as const;
};
```

- [ ] **Step 4: 运行测试并确认 GREEN**

Run: `cd frontend && node --test tests/desktopUpdater.test.ts`

Expected: 所有新增测试通过。

- [ ] **Step 5: 写安装进度、监听器清理和错误文案失败测试**

新增测试覆盖：

```ts
test('安装成功或失败都会注销状态与下载监听器', async () => {
  const cleanup: string[] = [];
  const progress: number[] = [];
  const win = runtime('win32');
  win.__TAURI__!.updater!.onUpdaterEvent = async (handler) => {
    handler({ status: 'PENDING' });
    return () => { cleanup.push('status'); };
  };
  win.__TAURI__!.event!.listen = async (_name, handler) => {
    handler({ payload: { chunkLength: 25, contentLength: 100 } });
    return () => { cleanup.push('progress'); };
  };
  await installDesktopUpdate(win, (event) => {
    if (event.percent !== null) progress.push(event.percent);
  });
  assert.deepEqual(progress, [25]);
  assert.deepEqual(cleanup.sort(), ['progress', 'status']);
});

test('签名错误不会被包装成可跳过提示', () => {
  assert.equal(
    desktopUpdateErrorMessage(new Error('signature verification failed')),
    '更新包签名验证失败，已取消安装。',
  );
});
```

失败分支将 `installUpdate` 替换为抛出异常，并再次断言两个 unlisten 都执行。

- [ ] **Step 6: 运行新增测试并确认 RED**

Run: `cd frontend && node --test tests/desktopUpdater.test.ts`

Expected: FAIL，`installDesktopUpdate` 或错误映射尚未实现。

- [ ] **Step 7: 实现安装和错误边界**

`installDesktopUpdate` 先注册 `onUpdaterEvent` 与 `tauri://update-download-progress`，再调用 `installUpdate`；使用 `try/finally` 执行两个 unlisten。下载事件累计 `chunkLength`，有 `contentLength > 0` 时返回 0–100 百分比，无总长度时 `percent: null`；累计达到总长度时发送 `phase: 'installing'`。错误映射至少覆盖：网络、404/JSON/manifest、signature、permission/access denied 和未知错误。

- [ ] **Step 8: 验证完整运行时服务**

Run: `cd frontend && node --test tests/desktopUpdater.test.ts`

Expected: 所有测试通过。

- [ ] **Step 9: 提交检查点（仅在用户明确授权提交后执行）**

```bash
git add frontend/src/services/desktopRuntime.ts frontend/src/services/desktopUpdater.ts frontend/tests/desktopUpdater.test.ts
git commit -m "feat: 增加 Windows 桌面更新运行时"
```

### Task 2: 建立可测试的更新状态机

**Files:**
- Create: `frontend/src/services/desktopUpdaterController.ts`
- Create: `frontend/tests/desktopUpdaterController.test.ts`

**Interfaces:**
- Consumes: Task 1 的 `DesktopUpdateCheckResult`、`DesktopUpdateManifest`、`DesktopUpdateProgress`。
- Produces: `DesktopUpdaterState`，阶段为 `unsupported | idle | checking | up_to_date | available | downloading | installing | error`。
- Produces: `createDesktopUpdaterController(adapter)`，公开 `initialize()`、`check()`、`install()`、`dismiss()`、`retry()` 和 `getState()`。

- [ ] **Step 1: 写“不自动检查”和并发门禁失败测试**

```ts
test('初始化只识别平台和版本，不检查更新', async () => {
  const calls: string[] = [];
  const controller = createDesktopUpdaterController({
    supported: async () => true,
    version: async () => '1.0.9',
    check: async () => { calls.push('check'); return { status: 'up_to_date' }; },
    install: async () => undefined,
  });
  await controller.initialize();
  assert.deepEqual(calls, []);
  assert.deepEqual(controller.getState(), { phase: 'idle', currentVersion: '1.0.9' });
});

test('检查进行中忽略第二次点击', async () => {
  // 用 deferred promise 暂停第一次检查；连续调用 check 两次，断言 adapter.check 只调用一次。
});
```

- [ ] **Step 2: 运行测试并确认 RED**

Run: `cd frontend && node --test tests/desktopUpdaterController.test.ts`

Expected: FAIL，提示找不到控制器模块。

- [ ] **Step 3: 实现初始化、检查和 dismiss 状态转换**

控制器内部只保存一份不可变状态；`initialize` 在非 Windows 环境进入 `unsupported`，Windows 环境只读取版本进入 `idle`。`check` 仅允许从 `idle | up_to_date | available | error` 进入 `checking`，成功后进入 `up_to_date` 或 `available`；失败进入 `error` 并保存 `retryAction: 'check'`。

- [ ] **Step 4: 验证初始状态与检查 GREEN**

Run: `cd frontend && node --test tests/desktopUpdaterController.test.ts`

Expected: 初始化和并发测试通过。

- [ ] **Step 5: 写下载、安装、重试和进度失败测试**

覆盖：

- `available -> downloading -> installing`。
- 进度回调写入 `downloadedBytes`、`totalBytes`、`percent`。
- `downloading/installing` 时 `dismiss()` 不关闭弹窗。
- 安装失败进入 `error`，`retry()` 重新执行安装而不是重新检查。
- `up_to_date` 和 `available` 可以 dismiss 回 `idle`，但保留当前版本。

- [ ] **Step 6: 运行测试并确认 RED**

Run: `cd frontend && node --test tests/desktopUpdaterController.test.ts`

Expected: FAIL，安装分支尚未实现。

- [ ] **Step 7: 实现安装与重试状态转换**

适配器的 `install(onProgress)` 返回 Promise。收到第一条进度前状态就是 `downloading`；状态事件进入安装阶段时切换 `installing`。成功时不主动 `relaunch`，因为 Tauri Windows updater 会重启；若 Promise 在未重启的测试环境中完成，状态保持 `installing` 并显示“应用即将重新启动”。

- [ ] **Step 8: 验证状态机 GREEN**

Run: `cd frontend && node --test tests/desktopUpdaterController.test.ts`

Expected: 所有控制器测试通过。

- [ ] **Step 9: 提交检查点（仅在用户明确授权提交后执行）**

```bash
git add frontend/src/services/desktopUpdaterController.ts frontend/tests/desktopUpdaterController.test.ts
git commit -m "feat: 增加桌面更新状态控制器"
```

### Task 3: 实现 B 版侧栏与应用内更新弹窗

**Files:**
- Create: `frontend/src/components/DesktopUpdater.vue`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/services/tour.ts`

**Interfaces:**
- Consumes: Task 2 的 `createDesktopUpdaterController`。
- Produces: `DesktopUpdater.vue`，自身初始化但不自动检查，Windows 支持时显示侧栏入口和 Teleport 弹窗。
- Produces: B 版“日常工作 / 数据配置 / 桌面应用”导航。

- [ ] **Step 1: 创建组件骨架并让构建先因缺失状态绑定失败**

在 `DesktopUpdater.vue` 中定义模板需要的状态，但先引用尚未声明的 `handleCheck`，并在 `App.vue` 挂载：

```vue
<DesktopUpdater :collapsed="isCollapsed" />
```

Run: `cd frontend && npm run build`

Expected: FAIL，`handleCheck` 未定义，证明新组件进入类型检查。

- [ ] **Step 2: 实现更新入口和弹窗状态**

组件挂载时只调用 `controller.initialize()`；不得调用 `controller.check()`。入口行为：

- `idle/up_to_date/available/error` 可点击检查。
- `checking` 显示旋转图标和“正在检查…”。
- `available` 图标显示蓝色提示点。
- 展开状态显示 `检查更新` 与 `v${currentVersion}`；折叠状态只显示图标和 tooltip。

弹窗按状态展示：

- `up_to_date`：当前版本和关闭按钮。
- `available`：新旧版本、日期、发布说明、“暂不更新”、“下载并安装”。
- `downloading`：确定或不确定进度条，不允许遮罩关闭。
- `installing`：签名校验/安装与即将重启提示。
- `error`：中文错误、“取消”和“重试”。

- [ ] **Step 3: 重整 App 左侧导航**

把现有名称和顺序调整为：

```text
日常工作
  工作台
  导入数据
  对账结果
数据配置（管理员）
  门店管理
  字段映射
桌面应用（由 DesktopUpdater 在 Windows 环境渲染）
  检查更新 · v1.0.9
本地服务正常
```

保留原路由、权限和折叠 localStorage 行为。将原“FRP Engine V1.0 (MVP)”硬编码版本删除，避免与实际桌面版本冲突。

- [ ] **Step 4: 更新新手引导文案和目标选择器**

导航名称改变后，检查 `tour.ts` 中对菜单和设置区域的文案/选择器。只更新实际受影响的条目，不新增更新器新手引导，因为更新是低频维护动作。

- [ ] **Step 5: 验证前端测试与生产构建**

Run: `cd frontend && npm test && npm run build`

Expected: Node 测试全部通过，Vue 类型检查和 Vite 构建成功。

- [ ] **Step 6: 人工开发态视觉检查**

在 Web 开发态确认“桌面应用”分组不显示；用测试注入或临时测试页渲染 Windows 状态，核对展开/折叠侧栏、长发布说明滚动、下载进度和 1280×820 默认窗口无溢出。临时测试代码不得保留。

- [ ] **Step 7: 提交检查点（仅在用户明确授权提交后执行）**

```bash
git add frontend/src/components/DesktopUpdater.vue frontend/src/App.vue frontend/src/services/tour.ts
git commit -m "feat: 增加侧栏桌面更新入口"
```

### Task 4: 生成并安全配置 Tauri 更新签名密钥

**Files:**
- Modify: `frontend/src-tauri/Cargo.toml`
- Modify: `frontend/src-tauri/tauri.conf.json`
- Create: `backend/tests/test_desktop_updater_configuration.py`
- Modify: `.github/workflows/release.yml`

**Interfaces:**
- Consumes: Tauri 1 signer 生成的公钥内容。
- Produces: 客户端信任公钥、GitHub `latest.json` endpoint、关闭默认 dialog、Windows passive 安装配置。
- External state: GitHub Secrets `TAURI_PRIVATE_KEY`、`TAURI_KEY_PASSWORD`，必须单独获得用户授权后创建。

- [ ] **Step 1: 写静态配置失败测试**

`backend/tests/test_desktop_updater_configuration.py` 读取 JSON、Cargo 文本和 workflow 文本，断言：

```python
def test_tauri_updater_is_signed_manual_and_https():
    config = load_tauri_config()
    updater = config["tauri"]["updater"]
    assert updater["active"] is True
    assert updater["dialog"] is False
    assert updater["endpoints"] == [
        "https://github.com/ones2three02/Financial-Reconciliation-Platform/"
        "releases/latest/download/latest.json"
    ]
    assert updater["pubkey"].strip()
    assert "PRIVATE KEY" not in updater["pubkey"]
    assert updater["windows"]["installMode"] == "passive"

def test_release_workflow_signs_and_prefers_nsis():
    workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    assert "secrets.TAURI_PRIVATE_KEY" in workflow
    assert "secrets.TAURI_KEY_PASSWORD" in workflow
    assert "updaterJsonPreferNsis: true" in workflow
    assert "uploadUpdaterJson: true" in workflow
```

同时断言 Cargo 的 `tauri` features 包含 `updater` 和 `os-all`。

- [ ] **Step 2: 运行配置测试并确认 RED**

Run: `PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -p no:cacheprovider backend/tests/test_desktop_updater_configuration.py -q`

Expected: FAIL，当前 Tauri 配置没有 updater。

- [ ] **Step 3: 用户授权后生成签名密钥，不把私钥输出到对话或日志**

先创建权限为 700 的本机目录，再通过 Tauri 1.6.3 signer 交互式生成：

```bash
install -d -m 700 "$HOME/.config/frp"
cd frontend
npx @tauri-apps/cli@1.6.3 signer generate -w "$HOME/.config/frp/updater.key"
chmod 600 "$HOME/.config/frp/updater.key"
chmod 644 "$HOME/.config/frp/updater.key.pub"
```

命令提示输入独立强密码。确认私钥 `updater.key` 和公钥 `updater.key.pub` 都存在；私钥文件保持在仓库外。不要在 shell history 中写明文密码。

- [ ] **Step 4: 配置 Tauri 1 updater**

在 Cargo features 增加 `updater`、`os-all`。在 `tauri.conf.json > tauri` 增加 updater 对象，其中非密钥字段必须为：

```json
"updater": {
  "active": true,
  "dialog": false,
  "endpoints": [
    "https://github.com/ones2three02/Financial-Reconciliation-Platform/releases/latest/download/latest.json"
  ],
  "windows": {
    "installMode": "passive"
  }
}
```

同时把 `"pubkey"` 设置为 `$HOME/.config/frp/updater.key.pub` 文件中的完整字符串；该字段必须与上述字段处于同一个 updater 对象。公钥配置后运行 `cargo check` 验证 JSON 能被 Tauri 反序列化。

- [ ] **Step 5: 更新 GitHub Actions 签名环境**

在 `tauri-action` 步骤的 `env` 加入：

```yaml
TAURI_PRIVATE_KEY: ${{ secrets.TAURI_PRIVATE_KEY }}
TAURI_KEY_PASSWORD: ${{ secrets.TAURI_KEY_PASSWORD }}
```

在 `with` 加入：

```yaml
uploadUpdaterJson: true
uploadUpdaterSignatures: true
updaterJsonPreferNsis: true
generateReleaseNotes: true
```

删除固定 `releaseBody`，或只保留简短人工摘要，让 GitHub Release Notes 成为弹窗说明来源。

- [ ] **Step 6: 用户授权后写入 GitHub Secrets**

私钥从文件标准输入写入，不打印内容：

```bash
gh secret set TAURI_PRIVATE_KEY < "$HOME/.config/frp/updater.key"
```

密码使用 `gh secret set TAURI_KEY_PASSWORD` 的隐藏交互输入。完成后只运行 `gh secret list` 确认名称存在，不读取 Secret 值。

- [ ] **Step 7: 验证配置 GREEN**

Run: `PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -p no:cacheprovider backend/tests/test_desktop_updater_configuration.py backend/tests/test_release_version.py -q`

Run: `cargo check --manifest-path frontend/src-tauri/Cargo.toml`

Expected: 配置测试通过，Rust/Tauri 配置编译成功。

- [ ] **Step 8: 提交检查点（仅在用户明确授权提交后执行）**

```bash
git add frontend/src-tauri/Cargo.toml frontend/src-tauri/Cargo.lock frontend/src-tauri/tauri.conf.json backend/tests/test_desktop_updater_configuration.py .github/workflows/release.yml
git commit -m "build: 配置 Windows 签名更新发布"
```

### Task 5: 校验 Release 更新清单并编写发布手册

**Files:**
- Create: `backend/scripts/verify_updater_manifest.py`
- Create: `backend/tests/test_updater_manifest.py`
- Modify: `.github/workflows/release.yml`
- Create: `docs/desktop/windows-update-release.md`

**Interfaces:**
- Produces: `validate_windows_updater_manifest(payload: dict, tag_name: str) -> dict[str, str]`。
- Produces: 发布后的 `verify-updater-release` GitHub Actions job。
- Produces: 不含 Secret 值的操作手册。

- [ ] **Step 1: 写更新清单失败测试**

```python
def test_valid_windows_nsis_manifest_is_accepted():
    payload = {
        "version": "v1.0.9",
        "platforms": {
            "windows-x86_64": {
                "url": "https://github.com/ones2three02/Financial-Reconciliation-Platform/"
                       "releases/download/v1.0.9/app.nsis.zip",
                "signature": "non-empty-signature",
            }
        },
    }
    assert validate_windows_updater_manifest(payload, "v1.0.9")["version"] == "1.0.9"

@pytest.mark.parametrize("missing", ["platform", "url", "signature"])
def test_incomplete_windows_manifest_is_rejected(missing):
    # 分别删除 windows-x86_64、url 或 signature，断言 ValueError 包含缺失项。
```

另外测试：版本与标签不一致、HTTP URL、URL 不指向当前标签、URL 不是 `.nsis.zip` 均拒绝。

- [ ] **Step 2: 运行测试并确认 RED**

Run: `PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -p no:cacheprovider backend/tests/test_updater_manifest.py -q`

Expected: FAIL，校验器模块不存在。

- [ ] **Step 3: 实现严格清单校验器和 CLI**

`validate_windows_updater_manifest`：

- 使用与现有版本脚本相同的 `vMAJOR.MINOR.PATCH` 规则。
- 允许 JSON `version` 带或不带 `v`，但必须等于标签。
- 只读取 `platforms.windows-x86_64`。
- URL 必须为 HTTPS、GitHub 当前仓库、当前标签路径并以 `.nsis.zip` 结尾。
- signature 去空白后非空。
- 返回规范化的 `version`、`url`、`signature`，CLI 成功只打印版本和 URL，不打印 signature。

- [ ] **Step 4: 验证校验器 GREEN**

Run: `PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -p no:cacheprovider backend/tests/test_updater_manifest.py -q`

Expected: 所有清单测试通过。

- [ ] **Step 5: 增加发布后验证 job**

在 workflow 增加依赖全部 matrix 构建的 job：

```yaml
verify-updater-release:
  needs: publish-tauri
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Download updater manifest
      run: >-
        curl --fail --location --retry 8 --retry-all-errors
        "https://github.com/ones2three02/Financial-Reconciliation-Platform/releases/download/${GITHUB_REF_NAME}/latest.json"
        --output latest.json
    - name: Verify Windows updater manifest
      run: python backend/scripts/verify_updater_manifest.py latest.json "${GITHUB_REF_NAME}"
```

该 job 失败时 Release 可能已创建，但工作流整体失败并明确标记不可作为应用内更新发布；不要自动删除 Release。

- [ ] **Step 6: 编写密钥与发布手册**

`windows-update-release.md` 必须写明：

- 私钥本机路径和权限要求，不记录密码。
- GitHub Secrets 名称和轮换限制。
- `1.0.9` 引导版本需要一次手动覆盖安装。
- 后续每次发布的版本修改、测试、提交、推送和标签步骤。
- GitHub Release 必须包含普通 NSIS `.exe`、`.nsis.zip`、`.sig`、`latest.json`。
- Windows 真机从旧版检查、下载、安装、重启、登录、数据保留的验收步骤。
- 私钥丢失时不得静默更换公钥，必须发布新的手动覆盖引导版本。

- [ ] **Step 7: 验证脚本、workflow 和文档无敏感内容**

Run: `PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -p no:cacheprovider backend/tests/test_updater_manifest.py backend/tests/test_desktop_updater_configuration.py -q`

Run: `rg -n "PRIVATE KEY|TAURI_KEY_PASSWORD=|TAURI_PRIVATE_KEY=" .github docs frontend backend --glob '!docs/superpowers/**'`

Expected: 测试通过；敏感扫描只允许出现 Secret 名称引用和安全说明，不出现密钥或密码值。

- [ ] **Step 8: 提交检查点（仅在用户明确授权提交后执行）**

```bash
git add backend/scripts/verify_updater_manifest.py backend/tests/test_updater_manifest.py .github/workflows/release.yml docs/desktop/windows-update-release.md
git commit -m "ci: 校验 Windows 更新发布产物"
```

### Task 6: 全量验证与 Windows 发布验收

**Files:**
- Modify as needed: only files already listed in Tasks 1–5
- Verify: repository-wide tests and Windows release artifacts

**Interfaces:**
- Consumes: Tasks 1–5 的完整实现。
- Produces: 本地验证证据、Windows CI 产物证据和真机验收记录。

- [ ] **Step 1: 执行前端完整验证**

Run: `cd frontend && npm test && npm run build`

Expected: Node 测试全部通过，Vue TypeScript 与 Vite 构建成功；允许现有大 chunk 警告，但不得有错误。

- [ ] **Step 2: 执行 Rust 验证**

Run: `cargo test --manifest-path frontend/src-tauri/Cargo.toml`

Run: `cargo clippy --manifest-path frontend/src-tauri/Cargo.toml --all-targets -- -D warnings`

Expected: 测试和 clippy 通过。依赖自身的 future-incompatibility 提示单独记录，不把第三方警告误报为本项目错误。

- [ ] **Step 3: 执行后端与静态发布验证**

Run: `PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -p no:cacheprovider backend/tests -q`

Run: `git diff --check`

Expected: 后端全量测试通过，无 whitespace 错误。

- [ ] **Step 4: 确认应用没有自动检查路径**

Run: `rg -n "checkForDesktopUpdate|checkUpdate" frontend/src`

Expected: 调用只存在于 `desktopUpdater.ts` 和用户点击处理器；`onMounted`、登录成功回调和 router guard 不调用检查函数。

- [ ] **Step 5: 用户授权后提交并推送桌面分支**

先检查 `git status --short` 和完整 diff，确保字段映射改动与更新器改动均属于当前桌面交付；使用 Conventional Commit 中文提交信息。推送目标只能是 `feature/desktop-tauri`，不得合并 `main`。

- [ ] **Step 6: 用户授权后发布 `v1.0.9` 引导版本**

确认 `tauri.conf.json` 版本仍为 `1.0.9` 且 Release 页面当前最新为 `v1.0.8`，再创建并推送 `v1.0.9` 标签。观察 GitHub Actions，确认 Windows job 和 `verify-updater-release` 成功；不得使用 force-push 或重用失败标签覆盖产物。

- [ ] **Step 7: 在 Windows 真机手动覆盖安装引导版本**

直接运行 `v1.0.9` NSIS 安装包覆盖旧版本，不卸载。确认：账号、SQLite 数据、门店和导入记录保留；左侧显示 B 版导航和 `检查更新 · v1.0.9`；点击后提示当前最新。

- [ ] **Step 8: 发布更高测试版本验证应用内闭环**

在用户授权的后续发布中把版本升到 `1.0.10`，发布说明包含可辨识测试文本。由 `v1.0.9` 手动检查并完成下载、签名校验、覆盖安装和重启，确认新版本号、登录、sidecar、数据库迁移与业务数据均正常。

- [ ] **Step 9: 记录最终状态与剩余风险**

交付说明必须区分：

- 本地代码和自动化测试是否通过。
- GitHub `latest.json` 是否真实可访问。
- Windows 真机更新闭环是否实际完成。
- 如果只完成代码而未发布/真机验证，状态必须写“部分完成，待 Windows 发布验收”，不能宣称自动更新已上线。
