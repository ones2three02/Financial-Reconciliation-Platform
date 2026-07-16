import json
from pathlib import Path

import pytest

from backend.scripts.create_updater_manifest import create_windows_updater_manifest
from backend.scripts.verify_updater_manifest import (
    validate_windows_updater_manifest,
)


def valid_manifest() -> dict:
    return {
        "version": "v1.0.9",
        "notes": "支持应用内更新",
        "platforms": {
            "windows-x86_64": {
                "url": (
                    "https://github.com/ones2three02/"
                    "Financial-Reconciliation-Platform/releases/download/"
                    "v1.0.9/frp_1.0.9_x64-setup.nsis.zip"
                ),
                "signature": "non-empty-signature",
            }
        },
    }


def test_valid_windows_nsis_manifest_is_accepted():
    assert validate_windows_updater_manifest(
        valid_manifest(),
        "v1.0.9",
    ) == {
        "version": "1.0.9",
        "url": (
            "https://github.com/ones2three02/"
            "Financial-Reconciliation-Platform/releases/download/"
            "v1.0.9/frp_1.0.9_x64-setup.nsis.zip"
        ),
        "signature": "non-empty-signature",
    }


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda payload: payload["platforms"].pop("windows-x86_64"), "windows-x86_64"),
        (lambda payload: payload["platforms"]["windows-x86_64"].pop("url"), "url"),
        (lambda payload: payload["platforms"]["windows-x86_64"].pop("signature"), "signature"),
    ],
)
def test_incomplete_windows_manifest_is_rejected(mutation, message):
    payload = valid_manifest()
    mutation(payload)

    with pytest.raises(ValueError, match=message):
        validate_windows_updater_manifest(payload, "v1.0.9")


def test_manifest_version_must_match_release_tag():
    payload = valid_manifest()
    payload["version"] = "1.0.10"

    with pytest.raises(ValueError, match="版本不一致"):
        validate_windows_updater_manifest(payload, "v1.0.9")


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/ones2three02/Financial-Reconciliation-Platform/releases/download/v1.0.9/app.nsis.zip",
        "https://example.com/releases/download/v1.0.9/app.nsis.zip",
        "https://github.com/ones2three02/Financial-Reconciliation-Platform/releases/download/v1.0.10/app.nsis.zip",
        "https://github.com/ones2three02/Financial-Reconciliation-Platform/releases/download/v1.0.9/app.msi.zip",
    ],
)
def test_manifest_only_accepts_current_github_nsis_asset(url):
    payload = valid_manifest()
    payload["platforms"]["windows-x86_64"]["url"] = url

    with pytest.raises(ValueError, match="NSIS 更新包地址无效"):
        validate_windows_updater_manifest(payload, "v1.0.9")


def test_manifest_cli_does_not_need_to_print_signature(tmp_path):
    path = tmp_path / "latest.json"
    path.write_text(json.dumps(valid_manifest()), encoding="utf-8")

    loaded = json.loads(path.read_text(encoding="utf-8"))
    result = validate_windows_updater_manifest(loaded, "v1.0.9")

    assert result["signature"] not in f"{result['version']} {result['url']}"


def test_create_windows_manifest_uses_signed_nsis_asset(tmp_path):
    signature = tmp_path / "app_1.0.11_x64-setup.nsis.zip.sig"
    signature.write_text("public-signature\n", encoding="utf-8")

    payload = create_windows_updater_manifest(
        signature,
        "v1.0.11",
        publication_date="2026-07-16T15:17:54Z",
    )

    assert payload["version"] == "1.0.11"
    assert payload["pub_date"] == "2026-07-16T15:17:54Z"
    assert payload["platforms"]["windows-x86_64"] == {
        "signature": "public-signature",
        "url": (
            "https://github.com/ones2three02/Financial-Reconciliation-Platform/"
            "releases/download/v1.0.11/app_1.0.11_x64-setup.nsis.zip"
        ),
    }


@pytest.mark.parametrize("filename", ["app.sig", "app.nsis.zip.sig.txt"])
def test_create_windows_manifest_rejects_invalid_asset_name(tmp_path, filename):
    signature = tmp_path / Path(filename).name
    signature.write_text("public-signature", encoding="utf-8")

    with pytest.raises(ValueError):
        create_windows_updater_manifest(signature, "v1.0.11")
