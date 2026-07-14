import argparse
import getpass

from backend.app.core.db import SessionLocal
from backend.app.services.auth_service import create_user


def main() -> int:
    parser = argparse.ArgumentParser(description="创建 FRP 管理员")
    parser.add_argument("username", help="管理员用户名")
    args = parser.parse_args()
    password = getpass.getpass("管理员密码（至少 12 位）: ")
    confirmation = getpass.getpass("再次输入管理员密码: ")
    if password != confirmation:
        raise SystemExit("两次输入的密码不一致")

    with SessionLocal() as db:
        user = create_user(
            db,
            username=args.username,
            password=password,
            role="admin",
        )
        db.commit()
        print(f"已创建管理员: {user.username}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
