"""Guard the release license inventory against dependency drift."""

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def _runtime_dependency_names():
    names = []
    for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        names.append(line.split(">=", 1)[0].split("==", 1)[0].strip())
    return names


def test_third_party_license_inventory_covers_runtime_dependencies():
    inventory = (ROOT / "THIRD_PARTY_LICENSES.txt").read_text(encoding="utf-8")

    assert "Checked: 2026-07-02" in inventory
    assert "licensed under MIT according to `LICENSE`" in inventory
    assert "not a frozen transitive SBOM" in inventory

    inventory_lower = inventory.lower()
    for package in _runtime_dependency_names():
        assert f"| {package.lower()} " in inventory_lower

    for package in ("PySide6_Addons", "PySide6_Essentials", "shiboken6"):
        assert f"| {package}" in inventory
