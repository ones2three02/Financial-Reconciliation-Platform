# Windows 桌面端可靠性修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不改变 Excel 导入业务流程的前提下，修复 Windows 桌面端冷启动登录、错误反馈、诊断日志、文件路径和发布版本一致性问题。

**Architecture:** Tauri Rust 宿主继续作为后端启动与 90 秒就绪等待的唯一负责人；前端严格获取并缓存一次桌面配置，失败时显式报错且允许重试。Python Sidecar 在用户应用数据目录写入有限滚动日志，发布流水线在打包前校验 Git 标签与 Tauri 安装包版本。

**Tech Stack:** Vue 3、TypeScript、Axios、Node test runner、Tauri 1、Rust、Python 3.11+、FastAPI、pytest、GitHub Actions

## Global Constraints

- 保留“创建当前账期批次后才能导入”的现有业务约束。
- 不修改 Excel 模板识别、预检、解析、入库与对账逻辑。
- 不自动创建账期批次，不改变导入按钮的业务启用条件。
- 不新增第三方依赖，不升级现有依赖大版本。
- 不记录桌面启动令牌、密码、会话令牌或导入文件内容。
- 不执行生产发布、创建标签、推送或触发发布流水线。
- Git 提交步骤仅在用户另行明确授权后执行；未获授权时跳过提交但保留完整验证记录。

---

## 文件结构

- `frontend/src/services/desktopRuntime.ts`：检测 Tauri、严格校验并加载动态后端配置。
- `frontend/src/services/desktopConnection.ts`：管理并发共享、失败可重试的桌面配置缓存。
- `frontend/src/services/api.ts`：在请求发送前应用桌面动态地址和启动令牌。
- `frontend/src/services/desktopSetup.ts`：首次管理员流程和桌面初始化错误的人类可读映射。
- `frontend/src/views/Login.vue`：显示初始化失败和重试入口。
- `frontend/src/services/download.ts`：跨平台父目录解析与打开操作。
- `frontend/src/components/DownloadTracker.vue`：跨平台文件夹文案。
- `backend/run.py`：桌面数据目录、滚动启动日志和阶段诊断。
- `backend/scripts/verify_desktop_version.py`：标签与 Tauri 版本一致性校验。
- `.github/workflows/release.yml`：发布构建前执行版本校验。
- `frontend/src-tauri/tauri.conf.json`：安装包版本更新到 `1.0.9`。

### Task 1: 严格加载并共享桌面后端配置

**Files:**
- Modify: `frontend/src/services/desktopRuntime.ts`
- Create: `frontend/src/services/desktopConnection.ts`
- Modify: `frontend/src/services/api.ts:1-30`
- Modify: `frontend/tests/desktopRuntime.test.ts`
- Create: `frontend/tests/desktopConnection.test.ts`

**Interfaces:**
- Consumes: Tauri 命令 `desktop_backend_config`，返回 `{ api_base_url: string; token: string }`。
- Produces: `loadDesktopBackendConfig(runtime): Promise<DesktopBackendConfig | null>`；`getDesktopBackendConfig(runtime): Promise<DesktopBackendConfig | null>`；`resetDesktopBackendConnection(): void`。

- [ ] **Step 1: 为严格错误传播补充失败测试**

在 `frontend/tests/desktopRuntime.test.ts` 保留非法回环地址测试，并追加：

```ts
test('Tauri IPC 启动失败时保留错误而不回退到 Web API', async () => {
  await assert.rejects(
    loadDesktopBackendConfig({
      location: { protocol: 'https:', hostname: 'tauri.localhost' },
      __TAURI__: {
        invoke: async () => { throw new Error('桌面后端未能在 90 秒内启动'); },
      },
    }),
    /90 秒内启动/,
  );
});
```

- [ ] **Step 2: 运行测试并确认 RED**

Run: `cd frontend && node --test tests/desktopRuntime.test.ts`

Expected: 非法配置测试继续以 `Missing expected rejection` 失败，证明实现仍在吞错。

- [ ] **Step 3: 移除前端 8 秒竞速和 catch-to-null**

将 `loadDesktopBackendConfig` 收敛为：

```ts
export const loadDesktopBackendConfig = async (
  runtime: RuntimeWindow,
): Promise<DesktopBackendConfig | null> => {
  if (!isTauriRuntime(runtime)) return null;
  if (!runtime.__TAURI__) throw new Error('Tauri IPC 接口不可用');
  const config = await runtime.__TAURI__.invoke<DesktopBackendConfig>('desktop_backend_config');
  return validateDesktopBackendConfig(config);
};
```

- [ ] **Step 4: 运行严格加载测试并确认 GREEN**

Run: `cd frontend && node --test tests/desktopRuntime.test.ts`

Expected: 4 tests pass，测试进程退出码为 0。

- [ ] **Step 5: 为并发共享与失败重试写测试**

创建 `frontend/tests/desktopConnection.test.ts`：

```ts
import assert from 'node:assert/strict';
import test from 'node:test';

import { createDesktopConnection } from '../src/services/desktopConnection.ts';

const runtime = { location: { protocol: 'https:', hostname: 'tauri.localhost' } };

test('并发请求共享同一次桌面配置加载', async () => {
  let calls = 0;
  const connection = createDesktopConnection(async () => {
    calls += 1;
    return { api_base_url: 'http://127.0.0.1:43123/api/v1', token: 'per-launch-secret' };
  });
  const [first, second] = await Promise.all([
    connection.get(runtime),
    connection.get(runtime),
  ]);
  assert.equal(calls, 1);
  assert.deepEqual(first, second);
});

test('失败不会被缓存且下一次可以重试', async () => {
  let calls = 0;
  const connection = createDesktopConnection(async () => {
    calls += 1;
    if (calls === 1) throw new Error('cold start failed');
    return { api_base_url: 'http://127.0.0.1:43123/api/v1', token: 'per-launch-secret' };
  });
  await assert.rejects(connection.get(runtime), /cold start failed/);
  assert.equal((await connection.get(runtime))?.token, 'per-launch-secret');
  assert.equal(calls, 2);
});
```

- [ ] **Step 6: 运行缓存测试并确认 RED**

Run: `cd frontend && node --test tests/desktopConnection.test.ts`

Expected: FAIL，模块 `desktopConnection.ts` 不存在。

- [ ] **Step 7: 实现最小桌面连接缓存**

创建 `frontend/src/services/desktopConnection.ts`：

```ts
import {
  loadDesktopBackendConfig,
  type DesktopBackendConfig,
  type RuntimeWindow,
} from './desktopRuntime';

type DesktopConfigLoader = (runtime: RuntimeWindow) => Promise<DesktopBackendConfig | null>;

export const createDesktopConnection = (load: DesktopConfigLoader = loadDesktopBackendConfig) => {
  let cached: DesktopBackendConfig | null | undefined;
  let pending: Promise<DesktopBackendConfig | null> | null = null;

  return {
    async get(runtime: RuntimeWindow) {
      if (cached !== undefined) return cached;
      if (!pending) {
        pending = load(runtime)
          .then((config) => {
            cached = config;
            return config;
          })
          .finally(() => { pending = null; });
      }
      return pending;
    },
    reset() {
      cached = undefined;
      pending = null;
    },
  };
};

const desktopConnection = createDesktopConnection();
export const getDesktopBackendConfig = (runtime: RuntimeWindow) => desktopConnection.get(runtime);
export const resetDesktopBackendConnection = () => desktopConnection.reset();
```

修改 `frontend/src/services/api.ts`，用 `getDesktopBackendConfig(window)` 替换文件内的 `cachedDesktopConfig`，只有返回非空配置时才覆盖 Axios `baseURL` 和令牌头。

- [ ] **Step 8: 验证桌面配置测试与前端类型构建**

Run: `cd frontend && node --test tests/desktopRuntime.test.ts tests/desktopConnection.test.ts`

Expected: 6 tests pass。

Run: `cd frontend && npm run build`

Expected: `vue-tsc -b` 与 Vite 构建退出码均为 0。

- [ ] **Step 9: 经用户授权后提交 Task 1**

```bash
git add frontend/src/services/desktopRuntime.ts frontend/src/services/desktopConnection.ts frontend/src/services/api.ts frontend/tests/desktopRuntime.test.ts frontend/tests/desktopConnection.test.ts
git commit -m "fix: 修复桌面后端配置初始化与重试"
```

### Task 2: 登录初始化错误反馈与重试

**Files:**
- Modify: `frontend/src/services/desktopSetup.ts`
- Modify: `frontend/tests/desktopSetup.test.ts`
- Modify: `frontend/src/views/Login.vue`

**Interfaces:**
- Consumes: `api.getDesktopSetupStatus()` 与 `resetDesktopBackendConnection()`。
- Produces: `desktopInitializationErrorMessage(error): string`；登录页 `initializeDesktop(forceReset?: boolean): Promise<void>`。

- [ ] **Step 1: 为错误映射写失败测试**

向 `frontend/tests/desktopSetup.test.ts` 增加：

```ts
test('桌面启动超时显示可重试提示', () => {
  assert.equal(
    desktopInitializationErrorMessage(new Error('桌面后端未能在 90 秒内启动')),
    '本地服务启动超时，请重试；若仍失败，请重新启动应用。',
  );
});

test('IPC 不可用显示桌面通信错误', () => {
  assert.equal(
    desktopInitializationErrorMessage(new Error('Tauri IPC 接口不可用')),
    '桌面通信接口不可用，请重新启动应用。',
  );
});
```

- [ ] **Step 2: 运行测试并确认 RED**

Run: `cd frontend && node --test tests/desktopSetup.test.ts`

Expected: FAIL，`desktopInitializationErrorMessage` 尚未导出。

- [ ] **Step 3: 实现安全的人类可读错误映射**

在 `frontend/src/services/desktopSetup.ts` 增加：

```ts
export const desktopInitializationErrorMessage = (error: unknown): string => {
  const message = error instanceof Error ? error.message : String(error ?? '');
  if (message.includes('90 秒') || message.includes('TimedOut') || message.includes('超时')) {
    return '本地服务启动超时，请重试；若仍失败，请重新启动应用。';
  }
  if (message.includes('IPC') || message.includes('Tauri')) {
    return '桌面通信接口不可用，请重新启动应用。';
  }
  if (message.includes('无效的桌面后端')) {
    return '桌面服务配置无效，请重新启动应用。';
  }
  return '桌面服务初始化失败，请重试；若仍失败，请重新启动应用。';
};
```

- [ ] **Step 4: 修改登录页为可重试初始化**

在 `Login.vue` 中：

```ts
const initializeDesktop = async (forceReset = false) => {
  if (!isTauriRuntime(window)) return;
  isInitializing.value = true;
  desktopInitializationFailed.value = false;
  errorMessage.value = '';
  if (forceReset) resetDesktopBackendConnection();
  try {
    setupRequired.value = (await api.getDesktopSetupStatus()).setup_required;
  } catch (error) {
    desktopInitializationFailed.value = true;
    errorMessage.value = desktopInitializationErrorMessage(error);
  } finally {
    isInitializing.value = false;
  }
};

onMounted(() => { void initializeDesktop(); });
```

错误提示区域下加入仅在桌面初始化失败时出现的按钮：

```vue
<Button
  v-if="desktopInitializationFailed"
  type="button"
  variant="outline"
  class="w-full border-rose-500/30 text-rose-300"
  :disabled="isInitializing"
  @click="initializeDesktop(true)"
>
  重试本地服务
</Button>
```

`desktopInitializationFailed` 仅表示 Tauri 环境下初始化完成但存在错误，登录按钮在该状态继续禁用，避免把请求发送到错误地址。

- [ ] **Step 5: 验证登录逻辑测试和构建**

Run: `cd frontend && node --test tests/desktopSetup.test.ts tests/desktopRuntime.test.ts tests/desktopConnection.test.ts`

Expected: 所有测试通过。

Run: `cd frontend && npm run build`

Expected: 构建退出码为 0。

- [ ] **Step 6: 经用户授权后提交 Task 2**

```bash
git add frontend/src/services/desktopSetup.ts frontend/tests/desktopSetup.test.ts frontend/src/views/Login.vue
git commit -m "fix: 增加桌面登录初始化错误与重试"
```

### Task 3: Windows Sidecar 滚动启动日志

**Files:**
- Modify: `backend/run.py`
- Modify: `backend/tests/test_desktop_runtime.py`

**Interfaces:**
- Consumes: 当前操作系统、环境变量和用户主目录。
- Produces: `desktop_data_dir(system, environment, home): Path`；`configure_desktop_logging(base_dir): logging.Logger`。

- [ ] **Step 1: 写桌面数据目录和滚动日志失败测试**

在 `backend/tests/test_desktop_runtime.py` 增加：

```python
def test_windows_desktop_data_dir_uses_appdata(tmp_path):
    assert run.desktop_data_dir(
        system="Windows",
        environment={"APPDATA": str(tmp_path)},
        home=tmp_path / "home",
    ) == tmp_path / "Financial-Reconciliation-Platform"


def test_desktop_logger_writes_rotating_log_without_secret(tmp_path):
    logger = run.configure_desktop_logging(tmp_path)
    logger.info("桌面后端启动 port=%s", 43123)
    for handler in logger.handlers:
        handler.flush()
    content = (tmp_path / "logs" / "desktop-backend.log").read_text(encoding="utf-8")
    assert "port=43123" in content
    assert "FRP_DESKTOP_TOKEN" not in content
```

- [ ] **Step 2: 运行测试并确认 RED**

Run: `PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -p no:cacheprovider backend/tests/test_desktop_runtime.py -q`

Expected: FAIL，两个新函数不存在。

- [ ] **Step 3: 实现数据目录与有限滚动日志**

在 `backend/run.py` 使用标准库：

```python
import logging
import platform
from collections.abc import Mapping
from logging.handlers import RotatingFileHandler

APP_DIR_NAME = "Financial-Reconciliation-Platform"


def desktop_data_dir(
    *,
    system: str | None = None,
    environment: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> Path:
    current_system = system or platform.system()
    current_environment = environment if environment is not None else os.environ
    current_home = home or Path.home()
    if current_system == "Windows":
        return Path(current_environment.get("APPDATA") or current_home) / APP_DIR_NAME
    if current_system == "Darwin":
        return current_home / "Library" / "Application Support" / APP_DIR_NAME
    return current_home / ".local" / "share" / APP_DIR_NAME


def configure_desktop_logging(base_dir: Path) -> logging.Logger:
    logger = logging.getLogger("frp.desktop")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        try:
            log_dir = base_dir / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            handler = RotatingFileHandler(
                log_dir / "desktop-backend.log",
                maxBytes=2 * 1024 * 1024,
                backupCount=3,
                encoding="utf-8",
            )
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            logger.addHandler(handler)
        except OSError:
            logger.addHandler(logging.NullHandler())
    return logger
```

`configure_desktop_database_url()` 复用 `desktop_data_dir()`，避免数据目录规则重复。

- [ ] **Step 4: 在主启动阶段记录安全诊断信息**

桌面分支按以下顺序执行：

```python
base_dir = desktop_data_dir()
logger = configure_desktop_logging(base_dir)
try:
    logger.info("桌面后端开始启动 port=%s frozen=%s", port, frozen)
    database_url = configure_desktop_database_url()
    logger.info("开始准备桌面数据库")
    prepare_desktop_backend(database_url)
    logger.info("桌面数据库准备完成")
except Exception:
    logger.exception("桌面后端启动失败")
    raise
```

不得把 `FRP_DESKTOP_TOKEN`、完整环境变量或数据库 URL 写入日志。

- [ ] **Step 5: 验证桌面运行时与数据库迁移测试**

Run: `PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -p no:cacheprovider backend/tests/test_desktop_runtime.py backend/tests/test_migrations.py -q`

Expected: 所有测试通过。

- [ ] **Step 6: 经用户授权后提交 Task 3**

```bash
git add backend/run.py backend/tests/test_desktop_runtime.py
git commit -m "fix: 增加 Windows 桌面后端启动日志"
```

### Task 4: 跨平台打开文件所在目录

**Files:**
- Modify: `frontend/src/services/download.ts`
- Create: `frontend/tests/download.test.ts`
- Modify: `frontend/src/components/DownloadTracker.vue`
- Modify: `frontend/src-tauri/tauri.conf.json`
- Modify: `backend/tests/test_release_version.py`

**Interfaces:**
- Consumes: 用户已保存文件的绝对路径。
- Produces: `parentDirectory(filePath): string | null`。

- [ ] **Step 1: 写 Windows、macOS 和边界路径测试**

创建 `frontend/tests/download.test.ts`：

```ts
import assert from 'node:assert/strict';
import test from 'node:test';

import { parentDirectory } from '../src/services/download.ts';

test('提取 Windows 文件父目录', () => {
  assert.equal(parentDirectory('C:\\Users\\finance\\对账结果.xlsx'), 'C:\\Users\\finance');
});

test('保留 Windows 盘符根目录', () => {
  assert.equal(parentDirectory('D:\\对账结果.xlsx'), 'D:\\');
});

test('提取 POSIX 文件父目录', () => {
  assert.equal(parentDirectory('/Users/finance/对账结果.xlsx'), '/Users/finance');
});

test('无父目录的文件名返回 null', () => {
  assert.equal(parentDirectory('对账结果.xlsx'), null);
});
```

- [ ] **Step 2: 运行测试并确认 RED**

Run: `cd frontend && node --test tests/download.test.ts`

Expected: FAIL，`parentDirectory` 尚未导出。

- [ ] **Step 3: 实现纯函数并复用到 openFolder**

在 `download.ts` 增加：

```ts
export const parentDirectory = (filePath: string): string | null => {
  const path = filePath.trim();
  const lastSlash = Math.max(path.lastIndexOf('/'), path.lastIndexOf('\\'));
  if (lastSlash < 0) return null;
  if (lastSlash === 0) return path.slice(0, 1);
  const withSeparator = path.slice(0, lastSlash + 1);
  if (/^[a-zA-Z]:[\\/]$/.test(withSeparator)) return withSeparator;
  return path.slice(0, lastSlash);
};
```

`openFolder` 只在返回非空父目录时调用 `tauri.shell.open(parentPath)`。

- [ ] **Step 4: 改跨平台文案**

将 `DownloadTracker.vue` 中的“在访达中显示”改为“打开所在文件夹”。

同时将 `tauri.conf.json` 的 `shell.open` 正则收紧为 `^(?:[a-zA-Z]:\\\\.*|/.*)$`，并测试 Windows/POSIX 绝对路径通过、相对路径和 URL 被拒绝。

- [ ] **Step 5: 验证下载测试和前端构建**

Run: `cd frontend && node --test tests/download.test.ts`

Expected: 4 tests pass。

Run: `cd frontend && npm run build`

Expected: 构建退出码为 0。

- [ ] **Step 6: 经用户授权后提交 Task 4**

```bash
git add frontend/src/services/download.ts frontend/tests/download.test.ts frontend/src/components/DownloadTracker.vue
git commit -m "fix: 修正 Windows 下载文件夹操作"
```

### Task 5: 发布版本一致性保护

**Files:**
- Create: `backend/scripts/verify_desktop_version.py`
- Create: `backend/tests/test_release_version.py`
- Modify: `frontend/src-tauri/tauri.conf.json:11`
- Modify: `.github/workflows/release.yml`

**Interfaces:**
- Consumes: 标签名 `vMAJOR.MINOR.PATCH` 与 Tauri JSON 配置路径。
- Produces: `validate_desktop_version(tag_name, config_path): str`，成功返回无 `v` 版本，失败抛出 `ValueError`。

- [ ] **Step 1: 写版本一致性失败测试**

创建 `backend/tests/test_release_version.py`：

```python
import json

import pytest

from backend.scripts.verify_desktop_version import validate_desktop_version


def write_config(tmp_path, version: str):
    path = tmp_path / "tauri.conf.json"
    path.write_text(json.dumps({"package": {"version": version}}), encoding="utf-8")
    return path


def test_matching_release_tag_is_accepted(tmp_path):
    assert validate_desktop_version("v1.0.9", write_config(tmp_path, "1.0.9")) == "1.0.9"


def test_mismatching_release_tag_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="版本不一致"):
        validate_desktop_version("v1.0.9", write_config(tmp_path, "1.0.8"))
```

- [ ] **Step 2: 运行测试并确认 RED**

Run: `PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -p no:cacheprovider backend/tests/test_release_version.py -q`

Expected: FAIL，校验模块不存在。

- [ ] **Step 3: 实现无依赖版本校验脚本**

创建 `backend/scripts/verify_desktop_version.py`：

```python
import json
import re
import sys
from pathlib import Path

VERSION_PATTERN = re.compile(r"^v(\d+\.\d+\.\d+)$")


def validate_desktop_version(tag_name: str, config_path: Path) -> str:
    match = VERSION_PATTERN.fullmatch(tag_name)
    if match is None:
        raise ValueError(f"发布标签格式无效: {tag_name}")
    tag_version = match.group(1)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    package_version = config["package"]["version"]
    if tag_version != package_version:
        raise ValueError(
            f"发布标签与桌面安装包版本不一致: {tag_version} != {package_version}"
        )
    return tag_version


if __name__ == "__main__":
    try:
        print(validate_desktop_version(sys.argv[1], Path(sys.argv[2])))
    except (IndexError, KeyError, OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(str(exc)) from exc
```

- [ ] **Step 4: 更新安装包版本和发布前校验**

将 `frontend/src-tauri/tauri.conf.json` 的 `package.version` 更新为 `1.0.9`。

在 `.github/workflows/release.yml` 的 `Set up Python` 后增加：

```yaml
      - name: Verify desktop release version
        shell: bash
        run: python backend/scripts/verify_desktop_version.py "${GITHUB_REF_NAME}" frontend/src-tauri/tauri.conf.json
```

该步骤仅校验，不创建标签、不发布。

- [ ] **Step 5: 验证版本测试和当前目标版本**

Run: `PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -p no:cacheprovider backend/tests/test_release_version.py -q`

Expected: 3 tests pass，其中包含本地绝对路径放行规则测试。

Run: `venv/bin/python backend/scripts/verify_desktop_version.py v1.0.9 frontend/src-tauri/tauri.conf.json`

Expected: 输出 `1.0.9`，退出码为 0。

- [ ] **Step 6: 经用户授权后提交 Task 5**

```bash
git add backend/scripts/verify_desktop_version.py backend/tests/test_release_version.py frontend/src-tauri/tauri.conf.json .github/workflows/release.yml
git commit -m "build: 校验桌面安装包发布版本"
```

### Task 6: 同步 CORS 测试并执行完整回归

**Files:**
- Modify: `backend/tests/test_authentication.py:150-168`
- Verify only: Excel 解析与导入实现文件保持无变更。

**Interfaces:**
- Consumes: `Settings.allowed_cors_origins` 当前桌面白名单。
- Produces: 与实际配置一致且明确区分 Web/桌面模式的测试。

- [ ] **Step 1: 更新桌面 CORS 期望值**

将断言更新为完整实际列表：

```python
assert desktop_settings.allowed_cors_origins == [
    "https://finance.example.com",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:1420",
    "tauri://localhost",
    "http://tauri.localhost",
    "https://tauri.localhost",
]
```

保留 Web 模式只含 `https://finance.example.com` 的断言。

- [ ] **Step 2: 验证后端桌面与认证测试**

Run: `PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -p no:cacheprovider backend/tests/test_desktop_runtime.py backend/tests/test_authentication.py backend/tests/test_release_version.py -q`

Expected: 所有测试通过。

- [ ] **Step 3: 运行前端完整测试**

Run: `cd frontend && npm test`

Expected: 现有及新增测试全部通过，0 fail。

- [ ] **Step 4: 运行前端生产构建**

Run: `cd frontend && npm run build`

Expected: `vue-tsc -b` 和 Vite 构建退出码为 0；现有大 chunk 提示可记录但不属于本次修复。

- [ ] **Step 5: 运行 Rust 单元测试与 Clippy**

Run: `cd frontend/src-tauri && cargo test`

Expected: 3 tests pass，0 fail。

Run: `cd frontend/src-tauri && cargo clippy --all-targets -- -D warnings`

Expected: 退出码为 0；依赖的 future-incompatibility 提示不属于项目代码告警。

- [ ] **Step 6: 运行后端完整测试**

Run: `PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -p no:cacheprovider backend/tests -q`

Expected: 所有测试通过，0 fail。

- [ ] **Step 7: 单独验证 Excel 样例回归**

Run: `PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -p no:cacheprovider backend/tests/test_example_acceptance.py backend/tests/test_workbook_preflight.py backend/tests/test_import_pipeline.py -q`

Expected: 15 tests pass，证明本次桌面修复未改变 Excel 解析与导入行为。

- [ ] **Step 8: 检查变更范围与敏感信息**

Run: `git diff --check`

Expected: 无空白错误。

Run: `git diff --stat && git status --short`

Expected: 仅出现本计划列出的桌面可靠性文件、设计文档和计划文档；Excel 解析与导入实现文件无变更。

Run: `rg -n "FRP_DESKTOP_TOKEN|access_token|password" backend/run.py`

Expected: 日志调用中不包含这些敏感字段；代码正常读取环境变量不等于写日志。

- [ ] **Step 9: 经用户授权后提交 Task 6 与文档**

```bash
git add backend/tests/test_authentication.py docs/superpowers/specs/2026-07-16-windows-desktop-reliability-design.md docs/superpowers/plans/2026-07-16-windows-desktop-reliability.md
git commit -m "test: 完善桌面端可靠性回归验证"
```

## 最终人工验收（Windows）

- [ ] 安装 `v1.0.9` NSIS 包，Windows 应用列表显示版本 `1.0.9`。
- [ ] 首次启动期间登录按钮显示“正在初始化本地服务”，超过 8 秒时不会提前报网络错误。
- [ ] 模拟 Sidecar 启动失败时，登录页显示可重试提示，点击“重试本地服务”会重新初始化。
- [ ] 正常登录后，文件导入仍要求先创建当前账期批次；创建批次后原导入流程不变。
- [ ] 下载对账结果后显示“打开所在文件夹”，可打开 Windows 保存目录。
- [ ] `%APPDATA%\\Financial-Reconciliation-Platform\\logs\\desktop-backend.log` 存在，且不含令牌、密码或导入数据。
