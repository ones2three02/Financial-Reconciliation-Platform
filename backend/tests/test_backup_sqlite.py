import sqlite3

from backend.scripts.backup_sqlite import backup_sqlite


def test_backup_sqlite_creates_readable_point_in_time_copy(tmp_path):
    source = tmp_path / "frp.db"
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE sample (value TEXT NOT NULL)")
        connection.execute("INSERT INTO sample (value) VALUES ('保留数据')")
        connection.commit()

    backup = backup_sqlite(source)

    assert backup.exists()
    assert backup != source
    with sqlite3.connect(backup) as connection:
        assert connection.execute("SELECT value FROM sample").fetchone() == ("保留数据",)
