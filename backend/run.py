import uvicorn
import os
import sys

# Add project root to path so "backend" package is discoverable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if __name__ == "__main__":
    # 在桌面端模式下自动将 SQLite 数据库文件定位至系统专属的用户应用数据目录下，防止 Program Files/Applications 读写受限
    if os.environ.get("FRP_DESKTOP") == "true" and not os.environ.get("DATABASE_URL"):
        import platform
        system = platform.system()
        if system == "Windows":
            appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
            base_dir = os.path.join(appdata, "Financial-Reconciliation-Platform")
        elif system == "Darwin":
            base_dir = os.path.expanduser("~/Library/Application Support/Financial-Reconciliation-Platform")
        else:
            base_dir = os.path.expanduser("~/.local/share/Financial-Reconciliation-Platform")
        os.makedirs(base_dir, exist_ok=True)
        db_path = os.path.join(base_dir, "frp.db")
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

    from backend.app.main import app
    is_frozen = getattr(sys, 'frozen', False)
    # PyInstaller 冻结打包的二进制文件不支持 reload，故在此做动态区分
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=not is_frozen)
