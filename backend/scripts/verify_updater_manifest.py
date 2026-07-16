import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


VERSION_PATTERN = re.compile(r"^v(\d+\.\d+\.\d+)$")
REPOSITORY_PATH = "/ones2three02/Financial-Reconciliation-Platform"


def _release_version(tag_name: str) -> str:
    match = VERSION_PATTERN.fullmatch(tag_name)
    if match is None:
        raise ValueError(f"发布标签格式无效: {tag_name}")
    return match.group(1)


def validate_windows_updater_manifest(
    payload: dict,
    tag_name: str,
) -> dict[str, str]:
    release_version = _release_version(tag_name)
    manifest_version = str(payload.get("version", "")).removeprefix("v")
    if manifest_version != release_version:
        raise ValueError(
            f"更新清单版本不一致: {manifest_version} != {release_version}"
        )

    platforms = payload.get("platforms")
    if not isinstance(platforms, dict) or "windows-x86_64" not in platforms:
        raise ValueError("更新清单缺少 windows-x86_64 平台")
    windows = platforms["windows-x86_64"]
    if not isinstance(windows, dict):
        raise ValueError("windows-x86_64 更新配置格式无效")

    url = str(windows.get("url", "")).strip()
    if not url:
        raise ValueError("windows-x86_64 更新配置缺少 url")
    signature = str(windows.get("signature", "")).strip()
    if not signature:
        raise ValueError("windows-x86_64 更新配置缺少 signature")

    parsed = urlparse(url)
    expected_prefix = f"{REPOSITORY_PATH}/releases/download/{tag_name}/"
    if (
        parsed.scheme != "https"
        or parsed.netloc != "github.com"
        or not parsed.path.startswith(expected_prefix)
        or not parsed.path.endswith(".nsis.zip")
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(f"Windows NSIS 更新包地址无效: {url}")

    return {
        "version": release_version,
        "url": url,
        "signature": signature,
    }


def main(manifest_path: Path, tag_name: str) -> None:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("更新清单根节点必须是对象")
    result = validate_windows_updater_manifest(payload, tag_name)
    print(f"Windows updater manifest {result['version']}: {result['url']}")


if __name__ == "__main__":
    try:
        main(Path(sys.argv[1]), sys.argv[2])
    except (IndexError, OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(str(exc)) from exc
