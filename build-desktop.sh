#!/bin/bash
set -e

echo "=== 1. 确保安装编译打包依赖 ==="
# 激活 python 虚拟环境并安装 pyinstaller 依赖
if [ -d "venv" ]; then
  source venv/bin/activate
  pip install -q pyinstaller==6.21.0
else
  echo "未找到 python venv 环境，请先安装虚拟环境并进行配置"
  exit 1
fi

echo "=== 2. 获取 Rust 平台 target-triple ==="
# 动态检测当前主机的 Rust 编译三元组名称，确保兼容 M1/M2 芯片与 Intel 芯片 Mac
TARGET_TRIPLE=$(rustc -vV | grep host | cut -d ' ' -f 2)
if [ -z "$TARGET_TRIPLE" ]; then
  echo "未检测到 Rust 编译器环境，请确保安装了 Rust (rustup)"
  exit 1
fi
echo "Host 平台三元组: $TARGET_TRIPLE"

# 创建 binaries 侧边程序存放目录
mkdir -p frontend/src-tauri/binaries

echo "=== 3. 使用 PyInstaller 编译 Python FastAPI 离线二进制服务 ==="
# --collect-all 自动加载 uvicorn 运行时依赖及其相关子模块，解决动态引用丢失问题
pyinstaller --onefile --clean -y \
  --name frp-backend \
  --collect-all uvicorn \
  --collect-all alembic \
  --collect-all backend \
  --add-data "backend/alembic.ini:backend" \
  --add-data "backend/migrations:backend/migrations" \
  backend/run.py

# 移动编译出来的单文件可执行二进制到 Tauri binaries 并重命名为 Sidecar 三元组规范
cp dist/frp-backend frontend/src-tauri/binaries/frp-backend-$TARGET_TRIPLE
xattr -cr frontend/src-tauri/binaries/frp-backend-$TARGET_TRIPLE || true

echo "=== 4. 自动生成桌面端各尺寸高清图标 ==="
# 既然我们已经有 switch_variant.sh 进行高清图标管理，这里注释掉强制重新生成，以防破坏已有的预置高清图标
# cd frontend
# sips -c 343 343 src/assets/hero.png --out src/assets/icon-source.png
# npx @tauri-apps/cli@1.6.3 icon src/assets/icon-source.png


echo "=== 5. 构建前端 Vue 3 静态页面 ==="
cd frontend
npm ci
npm run build

echo "=== 6. 执行 Tauri 打包编译桌面应用 ==="
npx @tauri-apps/cli@1.6.3 build

# 自动同步到 outputs 目录并清空 quarantine 标记（彻底解决首次冷启动时 Gatekeeper 对单文件进行安全扫描导致的 30 秒卡顿）
mkdir -p ../outputs
cp -R src-tauri/target/release/bundle/macos/财务自动对账平台.app ../outputs/
xattr -cr ../outputs/财务自动对账平台.app || true

echo "=== 桌面应用编译完成！ ==="
echo "在 outputs/ 下查收您的安装包，已默认完成 Gatekeeper 扫描免疫，支持秒开！"
