@echo off
echo === 1. 确保安装编译打包依赖 ===
if exist venv (
  call venv\Scripts\activate.bat
  pip install -q pyinstaller==6.21.0
  if errorlevel 1 exit /b 1
) else (
  echo 未找到 python venv 环境，请先安装虚拟环境并进行配置
  exit /b 1
)

echo === 2. 获取 Rust 平台 target-triple ===
for /f "tokens=2" %%i in ('rustc -vV ^| findstr host') do set TARGET_TRIPLE=%%i
if "%TARGET_TRIPLE%"=="" (
  echo 未检测到 Rust 编译器环境，请确保安装了 Rust (rustup)
  exit /b 1
)
echo Host 平台三元组: %TARGET_TRIPLE%

if not exist frontend\src-tauri\binaries (
  mkdir frontend\src-tauri\binaries
)

echo === 3. 使用 PyInstaller 编译 Python FastAPI 离线二进制服务 ===
pyinstaller --onefile --clean -y ^
  --name frp-backend ^
  --collect-all uvicorn ^
  --collect-all alembic ^
  --collect-all backend ^
  --add-data "backend/alembic.ini:backend" ^
  --add-data "backend/migrations:backend/migrations" ^
  backend\run.py
if errorlevel 1 exit /b 1

copy dist\frp-backend.exe frontend\src-tauri\binaries\frp-backend-%TARGET_TRIPLE%.exe
if errorlevel 1 exit /b 1

echo === 4. 自动生成桌面端各尺寸高清图标 ===
cd frontend
call npx @tauri-apps/cli@1.6.3 icon src\assets\icon-source.png
if errorlevel 1 exit /b 1

echo === 5. 构建前端 Vue 3 静态页面 ===
call npm ci
if errorlevel 1 exit /b 1
call npm run build
if errorlevel 1 exit /b 1

echo === 6. 执行 Tauri 打包编译桌面应用 ===
call npx @tauri-apps/cli@1.6.3 build
if errorlevel 1 exit /b 1

echo === 桌面应用编译完成！ ===
cd ..
