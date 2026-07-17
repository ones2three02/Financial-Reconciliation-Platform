import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

# 兼容直接以脚本方式运行（python backend/scripts/create_updater_manifest.py）
# 以及作为包导入（from backend.scripts.create_updater_manifest import ...）两种场景。
# 将脚本所在目录加入 sys.path，确保同包内 verify_updater_manifest 可被找到。
_SCRIPTS_DIR = Path(__file__).parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from verify_updater_manifest import (  # noqa: E402
    REPOSITORY_PATH,
    _release_version,
    validate_windows_updater_manifest,
)


def create_windows_updater_manifest(
    signature_path: Path,
    tag_name: str,
    *,
    publication_date: str | None = None,
) -> dict:
    if not signature_path.name.endswith(".nsis.zip.sig"):
        raise ValueError("Windows 更新签名文件必须以 .nsis.zip.sig 结尾")
    signature = signature_path.read_text(encoding="utf-8").strip()
    if not signature:
        raise ValueError("Windows 更新签名不能为空")

    version = _release_version(tag_name)
    updater_asset = signature_path.name.removesuffix(".sig")
    payload = {
        "version": version,
        "notes": f"Windows 桌面端更新 {tag_name}",
        "pub_date": publication_date or datetime.now(UTC).isoformat(),
        "platforms": {
            "windows-x86_64": {
                "signature": signature,
                "url": (
                    "https://github.com"
                    f"{REPOSITORY_PATH}/releases/download/{tag_name}/"
                    f"{quote(updater_asset)}"
                ),
            }
        },
    }
    validate_windows_updater_manifest(payload, tag_name)
    return payload


def main(signature_path: Path, tag_name: str, output_path: Path) -> None:
    payload = create_windows_updater_manifest(signature_path, tag_name)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Windows updater manifest {payload['version']}: {output_path}")


if __name__ == "__main__":
    try:
        main(Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]))
    except (IndexError, OSError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
