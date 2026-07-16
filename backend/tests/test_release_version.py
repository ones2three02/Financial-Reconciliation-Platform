import json
import re
from pathlib import Path

import pytest

from backend.scripts.verify_desktop_version import validate_desktop_version


def write_config(tmp_path, version: str):
    path = tmp_path / "tauri.conf.json"
    path.write_text(json.dumps({"package": {"version": version}}), encoding="utf-8")
    return path


def test_matching_release_tag_is_accepted(tmp_path):
    assert validate_desktop_version("v1.0.9", write_config(tmp_path, "1.0.9")) == "1.0.9"


def test_mismatching_release_tag_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="版本不一致"):
        validate_desktop_version("v1.0.9", write_config(tmp_path, "1.0.8"))


def test_shell_open_only_allows_absolute_local_paths():
    config_path = Path(__file__).resolve().parents[2] / "frontend" / "src-tauri" / "tauri.conf.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    pattern = config["tauri"]["allowlist"]["shell"]["open"]

    assert re.search(pattern, r"C:\Users\finance\对账结果.xlsx")
    assert re.search(pattern, "/Users/finance/对账结果.xlsx")
    assert re.search(pattern, "D:\\")
    assert re.search(pattern, "对账结果.xlsx") is None
    assert re.search(pattern, "https://example.com/report.xlsx") is None
