import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TAURI_CONFIG = PROJECT_ROOT / "frontend" / "src-tauri" / "tauri.conf.json"
CARGO_CONFIG = PROJECT_ROOT / "frontend" / "src-tauri" / "Cargo.toml"
RELEASE_WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "release.yml"
UPDATE_ENDPOINT = (
    "https://github.com/ones2three02/Financial-Reconciliation-Platform/"
    "releases/latest/download/latest.json"
)


def test_tauri_updater_is_signed_manual_and_https():
    config = json.loads(TAURI_CONFIG.read_text(encoding="utf-8"))
    updater = config["tauri"]["updater"]

    assert updater["active"] is True
    assert updater["dialog"] is False
    assert updater["endpoints"] == [UPDATE_ENDPOINT]
    assert updater["pubkey"].strip()
    assert "PRIVATE KEY" not in updater["pubkey"]
    assert updater["windows"]["installMode"] == "passive"
    assert config["tauri"]["allowlist"]["os"]["all"] is True


def test_cargo_enables_only_required_desktop_update_features():
    cargo = CARGO_CONFIG.read_text(encoding="utf-8")

    assert '"updater"' in cargo
    assert '"os-all"' in cargo


def test_release_workflow_signs_and_prefers_nsis():
    workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")

    assert "secrets.TAURI_PRIVATE_KEY" in workflow
    assert "secrets.TAURI_KEY_PASSWORD" in workflow
    assert "includeUpdaterJson: false" in workflow
    assert "uploadUpdaterJson" not in workflow
    assert "uploadUpdaterSignatures" not in workflow
    assert "updaterJsonPreferNsis: true" in workflow
    assert 'args: "--bundles nsis,updater"' in workflow
    assert "create_updater_manifest.py" in workflow
    assert "gh release upload" in workflow
    assert "verify_updater_manifest.py" in workflow
