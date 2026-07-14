import argparse
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path


def backup_sqlite(source: Path, destination: Path | None = None) -> Path:
    source_path = source.expanduser().resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"SQLite 数据库不存在: {source_path}")
    if destination is None:
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        destination_path = source_path.with_name(
            f"{source_path.stem}.backup-{timestamp}{source_path.suffix}"
        )
    else:
        destination_path = destination.expanduser().resolve()
    if destination_path == source_path:
        raise ValueError("备份目标不能覆盖源数据库")
    if destination_path.exists():
        raise FileExistsError(f"备份目标已存在: {destination_path}")

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    partial_path = destination_path.with_suffix(f"{destination_path.suffix}.partial")
    try:
        with sqlite3.connect(source_path) as source_db, sqlite3.connect(partial_path) as target_db:
            source_db.backup(target_db)
        os.replace(partial_path, destination_path)
    except Exception:
        partial_path.unlink(missing_ok=True)
        raise
    return destination_path


def main() -> int:
    parser = argparse.ArgumentParser(description="安全备份本地 SQLite 数据库")
    parser.add_argument("source", type=Path, help="源数据库路径")
    parser.add_argument("--output", type=Path, help="可选的备份输出路径")
    args = parser.parse_args()
    backup_path = backup_sqlite(args.source, args.output)
    print(backup_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
