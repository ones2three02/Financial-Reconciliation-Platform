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
# 使用 --onedir 模式进行编译，消除 --onefile 模式在冷启动时解压到临时目录造成的长达几十秒的严重卡顿和系统安全扫描延迟
pyinstaller --onedir --clean -y \
  --name frp-backend-dir \
  --collect-all uvicorn \
  --collect-all alembic \
  --collect-all backend \
  --add-data "backend/alembic.ini:backend" \
  --add-data "backend/migrations:backend/migrations" \
  backend/run.py

# 创建 resources 目录并拷贝整个后端文件夹作为 Tauri 资源打包
mkdir -p frontend/src-tauri/resources
rm -rf frontend/src-tauri/resources/frp-backend-dir
cp -R dist/frp-backend-dir frontend/src-tauri/resources/
xattr -cr frontend/src-tauri/resources/frp-backend-dir || true

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
# 备份 tauri.conf.json 以便在退出时自动还原
cp src-tauri/tauri.conf.json src-tauri/tauri.conf.json.bak
restore_config() {
  if [ -f src-tauri/tauri.conf.json.bak ]; then
    mv src-tauri/tauri.conf.json.bak src-tauri/tauri.conf.json
  fi
}
trap restore_config EXIT

# 临时将 updater.active 设为 false 以防本地打包缺少私钥报错
node -e "
  const fs = require('fs');
  const path = 'src-tauri/tauri.conf.json';
  const config = JSON.parse(fs.readFileSync(path, 'utf8'));
  config.tauri.updater.active = false;
  fs.writeFileSync(path, JSON.stringify(config, null, 2), 'utf8');
"

npx @tauri-apps/cli@1.6.3 build

# 自动同步到 outputs 目录并清空 quarantine 标记（彻底解决首次冷启动时 Gatekeeper 对单文件进行安全扫描导致的 30 秒卡顿）
mkdir -p ../outputs
cp -R src-tauri/target/release/bundle/macos/财务自动对账平台.app ../outputs/
xattr -cr ../outputs/财务自动对账平台.app || true

# 将清除隔离后的 .app 压缩为 zip 绿色便携免安装版
echo "=== 7. 打包 macOS 绿色便携免安装版 ==="
cd ../outputs
rm -f 财务自动对账平台-macOS便携免安装版.zip
zip -q -r -y 财务自动对账平台-macOS便携免安装版.zip 财务自动对账平台.app
cd ../frontend

echo "=== 桌面应用编译完成！ ==="
echo "在 outputs/ 下查收您的安装包、DMG 镜像及 ZIP 绿色便携版，支持秒开！"
