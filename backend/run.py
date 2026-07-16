import os
import sys
from pathlib import Path

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


def configure_desktop_database_url() -> str:
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    import platform

    system = platform.system()
    if system == "Windows":
        base_dir = Path(os.environ.get("APPDATA") or Path.home()) / "Financial-Reconciliation-Platform"
    elif system == "Darwin":
        base_dir = Path.home() / "Library" / "Application Support" / "Financial-Reconciliation-Platform"
    else:
        base_dir = Path.home() / ".local" / "share" / "Financial-Reconciliation-Platform"
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

    if desktop:
        prepare_desktop_backend(configure_desktop_database_url())

    options = build_uvicorn_options(desktop=desktop, frozen=frozen, port=port)
    if desktop or frozen:
        from backend.app.main import app

        uvicorn.run(app, **options)
    else:
        uvicorn.run("backend.app.main:app", **options)


if __name__ == "__main__":
    main()
