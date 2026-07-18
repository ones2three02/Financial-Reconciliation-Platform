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
rem 使用 --onedir 模式进行编译，消除 --onefile 模式在冷启动时解压到临时目录造成的卡顿和系统扫描延迟
pyinstaller --onedir --noconsole --clean -y ^
  --name frp-backend-dir ^
  --collect-all uvicorn ^
  --collect-all alembic ^
  --collect-all backend ^
  --add-data "backend/alembic.ini;backend" ^
  --add-data "backend/migrations;backend/migrations" ^
  backend\run.py
if errorlevel 1 exit /b 1

rem 拷贝整个后端文件夹作为 Tauri 资源打包
if not exist frontend\src-tauri\resources (
  mkdir frontend\src-tauri\resources
)
if exist frontend\src-tauri\resources\frp-backend-dir (
  rmdir /s /q frontend\src-tauri\resources\frp-backend-dir
)
xcopy /e /i /y dist\frp-backend-dir frontend\src-tauri\resources\frp-backend-dir
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

echo === 7. 整理输出文件并打包 Windows 绿色便携免安装版 ===
cd ..
if not exist outputs (
  mkdir outputs
)

rem 1. 复制 MSI 安装包至 outputs 目录
if exist frontend\src-tauri\target\release\bundle\msi (
  copy /y frontend\src-tauri\target\release\bundle\msi\*.msi outputs\
)

rem 2. 创建便携免安装绿色版压缩包
if exist outputs\portable_temp (
  rmdir /s /q outputs\portable_temp
)
mkdir outputs\portable_temp
copy /y frontend\src-tauri\target\release\财务自动对账平台.exe outputs\portable_temp\
if not exist outputs\portable_temp\resources\frp-backend-dir (
  mkdir outputs\portable_temp\resources\frp-backend-dir
)
xcopy /e /i /y frontend\src-tauri\resources\frp-backend-dir outputs\portable_temp\resources\frp-backend-dir

rem 调用 PowerShell 压缩为 zip 便携版
powershell -Command "Compress-Archive -Path 'outputs\portable_temp\*' -DestinationPath 'outputs\财务自动对账平台-Windows便携免安装版.zip' -Force"

rem 清理临时目录
rmdir /s /q outputs\portable_temp

echo === 桌面应用编译与便携版打包完成！ ===
echo 在 outputs/ 下查收您的 MSI 安装包及 ZIP 绿色便携版。
