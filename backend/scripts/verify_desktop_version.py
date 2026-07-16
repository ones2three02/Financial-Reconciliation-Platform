import json
import re
import sys
from pathlib import Path


VERSION_PATTERN = re.compile(r"^v(\d+\.\d+\.\d+)$")


def validate_desktop_version(tag_name: str, config_path: Path) -> str:
    match = VERSION_PATTERN.fullmatch(tag_name)
    if match is None:
        raise ValueError(f"发布标签格式无效: {tag_name}")
    tag_version = match.group(1)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    package_version = config["package"]["version"]
    if tag_version != package_version:
        raise ValueError(
            f"发布标签与桌面安装包版本不一致: {tag_version} != {package_version}"
        )
    return tag_version


if __name__ == "__main__":
    try:
        print(validate_desktop_version(sys.argv[1], Path(sys.argv[2])))
    except (IndexError, KeyError, OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(str(exc)) from exc
