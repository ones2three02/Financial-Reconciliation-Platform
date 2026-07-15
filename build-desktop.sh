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

echo "=== 4. 自动生成桌面端各尺寸高清图标 ==="
cd frontend
# 用 sips 将主图裁切为正方形，避开 @tauri-apps/cli 的正方形输入源强校验
sips -c 343 343 src/assets/hero.png --out src/assets/icon-source.png
npx @tauri-apps/cli@1.6.3 icon src/assets/icon-source.png


echo "=== 5. 构建前端 Vue 3 静态页面 ==="
npm ci
npm run build

echo "=== 6. 执行 Tauri 打包编译桌面应用 ==="
npx @tauri-apps/cli@1.6.3 build

echo "=== 桌面应用编译完成！ ==="
echo "在 frontend/src-tauri/target/release/bundle/ 下查收您的安装包 (.dmg/.app)"
