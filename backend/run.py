import logging
import os
import platform
import sys
from collections.abc import Mapping
from logging.handlers import RotatingFileHandler
from pathlib import Path


APP_DIR_NAME = "Financial-Reconciliation-Platform"

# Fix: PyInstaller --noconsole mode will set sys.stdout/sys.stderr to None on Windows,
# which causes Uvicorn configure_logging to crash with "AttributeError: 'NoneType' object has no attribute 'isatty'"
class DummyStream:
    def write(self, *args, **kwargs): pass
    def flush(self, *args, **kwargs): pass
    def isatty(self): return False

if sys.stdout is None:
    sys.stdout = DummyStream()
if sys.stderr is None:
    sys.stderr = DummyStream()

import uvicorn

# Add project root to path so "backend" package is discoverable
if getattr(sys, "frozen", False):
    sys.path.insert(0, sys._MEIPASS)
else:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def build_uvicorn_options(*, desktop: bool, frozen: bool, port: int) -> dict[str, object]:
    return {
        "host": "127.0.0.1",
        "port": port,
        "reload": not desktop and not frozen,
    }


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
    logger = logging.getLogger(f"frp.desktop.{base_dir.resolve()}")
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


def configure_desktop_database_url(base_dir: Path | None = None) -> str:
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    base_dir = base_dir or desktop_data_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    database_url = f"sqlite:///{base_dir / 'frp.db'}"
    os.environ["DATABASE_URL"] = database_url
    return database_url


def prepare_desktop_backend(database_url: str) -> None:
    from backend.app.core.desktop_database import prepare_desktop_database

    prepare_desktop_database(database_url)
    from backend.app.core.db import SessionLocal
    from backend.app.services.auth_service import remove_insecure_seeded_admin

    with SessionLocal() as db:
        if remove_insecure_seeded_admin(db):
            db.commit()


def main() -> None:
    desktop = os.environ.get("FRP_DESKTOP", "").casefold() == "true"
    frozen = getattr(sys, "frozen", False)
    port = int(os.environ.get("FRP_PORT", "8000"))
    if not 1 <= port <= 65535:
        raise ValueError("FRP_PORT 必须在 1 到 65535 之间")

    desktop_logger: logging.Logger | None = None
    if desktop:
        base_dir = desktop_data_dir()
        desktop_logger = configure_desktop_logging(base_dir)
        try:
            desktop_logger.info("桌面后端开始启动 port=%s frozen=%s", port, frozen)
            database_url = configure_desktop_database_url(base_dir)
            desktop_logger.info("开始准备桌面数据库")
            prepare_desktop_backend(database_url)
            desktop_logger.info("桌面数据库准备完成")
        except Exception:
            desktop_logger.exception("桌面后端启动失败")
            raise

    options = build_uvicorn_options(desktop=desktop, frozen=frozen, port=port)
    if desktop or frozen:
        try:
            from backend.app.main import app

            if desktop_logger is not None:
                desktop_logger.info("启动 Uvicorn host=127.0.0.1 port=%s", port)
            uvicorn.run(app, **options)
        except Exception:
            if desktop_logger is not None:
                desktop_logger.exception("桌面后端运行失败")
            raise
    else:
        uvicorn.run("backend.app.main:app", **options)


if __name__ == "__main__":
    main()
