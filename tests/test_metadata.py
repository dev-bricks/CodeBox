"""Automated metadata, manifest, and contract parity test suite for CodeBox."""

import json
import re
import tomllib
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def pyproject_data() -> dict:
    pyproject_path = PROJECT_ROOT / "pyproject.toml"
    assert pyproject_path.is_file(), "pyproject.toml not found in project root"
    with open(pyproject_path, "rb") as f:
        return tomllib.load(f)


def test_version_parity(pyproject_data: dict) -> None:
    """Ensure version parity across pyproject.toml, version.py, READMEs, llms.txt, and CHANGELOG.md."""
    toml_version = pyproject_data.get("project", {}).get("version")
    assert toml_version is not None, "pyproject.toml missing project.version"

    # Check version.py
    import version

    assert version.APP_VERSION == toml_version, (
        f"version.py APP_VERSION ({version.APP_VERSION}) != pyproject.toml ({toml_version})"
    )
    assert version.__version__ == toml_version, (
        f"version.py __version__ ({version.__version__}) != pyproject.toml ({toml_version})"
    )

    # Check CHANGELOG.md contains the version section
    changelog_text = (PROJECT_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"[{toml_version}]" in changelog_text, (
        f"CHANGELOG.md missing release section for [{toml_version}]"
    )

    # Check README.md and README_de.md badges
    readme_en = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    readme_de = (PROJECT_ROOT / "README_de.md").read_text(encoding="utf-8")
    assert f"version-{toml_version}" in readme_en
    assert f"version-{toml_version}" in readme_de

    # Check llms.txt
    llms_text = (PROJECT_ROOT / "llms.txt").read_text(encoding="utf-8")
    assert re.search(r"Last-checked:\s*\d{4}-\d{2}-\d{2}", llms_text) is not None


def test_pyproject_required_fields(pyproject_data: dict) -> None:
    """Verify all expected project metadata fields exist in pyproject.toml."""
    proj = pyproject_data.get("project", {})
    assert proj.get("name") == "CodeBox"
    assert proj.get("description")
    assert proj.get("requires-python")
    assert proj.get("license", {}).get("text") == "MIT"
    assert isinstance(proj.get("authors"), list) and len(proj["authors"]) > 0
    assert isinstance(proj.get("keywords"), list) and len(proj["keywords"]) >= 20
    assert isinstance(proj.get("classifiers"), list) and len(proj["classifiers"]) >= 10

    urls = proj.get("urls", {})
    assert "Homepage" in urls
    assert "Repository" in urls
    assert "Issues" in urls
    assert "Changelog" in urls
    assert "Security" in urls
    assert "Notice" in urls
    assert "SBOM" in urls
    assert "Parent Org" in urls
    assert "Umbrella Ecosystem" in urls

    license_files = proj.get("license-files", [])
    assert "LICENSE" in license_files
    assert "NOTICE" in license_files
    assert "THIRD_PARTY_LICENSES.md" in license_files


def test_core_documentation_files_exist() -> None:
    """Ensure all standard documentation, notice, and license files exist and are non-empty."""
    required_files = [
        "README.md",
        "README_de.md",
        "llms.txt",
        "CHANGELOG.md",
        "LICENSE",
        "NOTICE",
        "SECURITY.md",
        "DEVELOPMENT_PLAN.md",
        "API_STATUS.md",
        "THIRD_PARTY_LICENSES.md",
        "THIRD_PARTY_LICENSES.txt",
        "MARKETING-LOG.txt",
    ]
    for filename in required_files:
        p = PROJECT_ROOT / filename
        assert p.is_file(), f"Missing required file: {filename}"
        assert p.stat().st_size > 0, f"File is empty: {filename}"


def test_bilingual_readme_parity_and_anchors() -> None:
    """Ensure English and German READMEs have corresponding headers, 18-point quick navigation, and dual anchors."""
    readme_en = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    readme_de = (PROJECT_ROOT / "README_de.md").read_text(encoding="utf-8")

    # Both must cross-link
    assert "[Deutsch](README_de.md)" in readme_en
    assert "[English](README.md)" in readme_de

    # Check key badges
    for text in [readme_en, readme_de]:
        assert "img.shields.io/badge/License-MIT" in text or "img.shields.io/badge/Lizenz-MIT" in text
        assert "Attribution-NOTICE" in text
        assert "SBOM-Level%201" in text
        assert "ecosystem-dev--bricks" in text
        assert "part%20of-open--bricks" in text
        assert re.search(r"tests-\d+%20passed", text) is not None
        assert "llms.txt" in text
        assert "SECURITY.md" in text

    # Check quick navigation section with 18 numbered points
    assert "## Quick Navigation" in readme_en
    assert "## Schnellnavigation" in readme_de
    for i in range(1, 19):
        assert f"- [{i}." in readme_en, f"README.md missing quick navigation item {i}."
        assert f"- [{i}." in readme_de, f"README_de.md missing schnellnavigation item {i}."

    # Check reciprocal HTML anchors exist in both READMEs
    anchors = [
        "start-here", "schnellstart",
        "system-architecture", "systemarchitektur",
        "end-to-end-workflow-lifecycle", "end-to-end-workflow-lebenszyklus",
        "key-capabilities--runtime-invariants", "kernfaehigkeiten--laufzeitinvarianten",
        "visual-showcase", "visuelle-demonstration",
        "target-personas--use-cases", "zielgruppen--anwendungsfaelle",
        "comparative-matrix-vs-alternatives", "vergleichsmatrix-gegenueber-alternativen",
        "features", "funktionsumfang",
        "installation--quickstart", "installation--schnellstart",
        "language-server-protocol-lsp-setup", "lsp-einrichtung",
        "declarative-plugin-system", "deklaratives-plugin-system",
        "local-windows-build", "lokaler-windows-build",
        "project-structure", "projektstruktur",
        "sibling-ecosystem", "geschwister-oekosystem",
        "search--disambiguation", "suche--abgrenzung",
        "third-party-licenses--level-1-sbom", "drittanbieter-lizenzen--level-1-sbom",
        "security--privacy", "sicherheit--datenschutz",
        "license--liability", "lizenz--haftung",
    ]
    for anchor in anchors:
        assert f'id="{anchor}"' in readme_en, f"Anchor {anchor} missing in README.md"
        assert f'id="{anchor}"' in readme_de, f"Anchor {anchor} missing in README_de.md"


def test_target_personas_and_comparative_matrix_invariants() -> None:
    """Verify personas [PERSONA-01]..[PERSONA-04] and invariants INV-LOCAL-01..INV-SLA-10."""
    readme_en = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    readme_de = (PROJECT_ROOT / "README_de.md").read_text(encoding="utf-8")
    sbom_text = (PROJECT_ROOT / "THIRD_PARTY_LICENSES.md").read_text(encoding="utf-8")

    personas = [f"[PERSONA-0{i}]" for i in range(1, 5)]
    for p in personas:
        assert p in readme_en, f"Persona {p} missing in README.md"
        assert p in readme_de, f"Persona {p} missing in README_de.md"

    invariants = [
        "INV-LOCAL-01",
        "INV-PERF-02",
        "INV-LGPL-03",
        "INV-CRASH-04",
        "INV-LSP-05",
        "INV-TERM-06",
        "INV-PLUG-07",
        "INV-PORT-08",
        "INV-GIT-09",
        "INV-SLA-10",
    ]
    for inv in invariants:
        assert inv in readme_en, f"Invariant {inv} missing in README.md"
        assert inv in readme_de, f"Invariant {inv} missing in README_de.md"
        assert inv in sbom_text, f"Invariant {inv} missing in THIRD_PARTY_LICENSES.md"


def test_notice_and_statutory_liability_disclaimer() -> None:
    """Ensure root NOTICE and statutory liability (§ 521 BGB) are present across docs."""
    notice_text = (PROJECT_ROOT / "NOTICE").read_text(encoding="utf-8")
    assert "Lukas Geiger" in notice_text
    assert "dev-bricks" in notice_text
    assert "open-bricks" in notice_text

    readme_en = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    readme_de = (PROJECT_ROOT / "README_de.md").read_text(encoding="utf-8")
    llms_text = (PROJECT_ROOT / "llms.txt").read_text(encoding="utf-8")

    for doc in [readme_en, readme_de, llms_text]:
        assert "521 BGB" in doc, "§ 521 BGB disclaimer missing in doc"


def test_mermaid_diagrams_syntax() -> None:
    """Verify both README files contain valid Mermaid flowchart and sequenceDiagram blocks."""
    readme_en = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    readme_de = (PROJECT_ROOT / "README_de.md").read_text(encoding="utf-8")

    for name, content in [("README.md", readme_en), ("README_de.md", readme_de)]:
        flowchart_matches = re.findall(r"```mermaid\s+flowchart\s+TD([\s\S]*?)```", content)
        assert len(flowchart_matches) >= 1, f"Missing flowchart TD in {name}"
        assert "subgraph UI" in flowchart_matches[0]
        assert "subgraph Core" in flowchart_matches[0]
        assert "subgraph Diagnostics" in flowchart_matches[0]

        sequence_matches = re.findall(r"```mermaid\s+sequenceDiagram([\s\S]*?)```", content)
        assert len(sequence_matches) >= 1, f"Missing sequenceDiagram in {name}"
        assert "autonumber" in sequence_matches[0]
        assert "Dev->>UI" in sequence_matches[0]
        assert "LSP" in sequence_matches[0]


def test_sibling_ecosystem_and_urls() -> None:
    """Verify sibling ecosystem table and links in READMEs."""
    readme_en = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    readme_de = (PROJECT_ROOT / "README_de.md").read_text(encoding="utf-8")

    for text in [readme_en, readme_de]:
        assert "safe-start-for-codex" in text
        assert "companion-for-agy" in text
        assert "automation-master" in text
        assert "automizer-for-claude-desktop" in text
        assert "ellmos-codecommander-mcp" in text
        assert "CleanMarkdown" in text
        assert "ExplorerPro" in text


def test_security_policy_and_offline_invariants() -> None:
    """Verify SECURITY.md bilingual structure, supported versions table, and zero-egress guarantees."""
    sec_path = PROJECT_ROOT / "SECURITY.md"
    assert sec_path.is_file()
    sec_text = sec_path.read_text(encoding="utf-8")

    # Bilingual headers
    assert "## English" in sec_text
    assert "## Deutsch" in sec_text

    # Security contacts
    assert "security@ellmos.ai" in sec_text
    assert "lukas@open-bricks.org" in sec_text
    assert "support@lukasgeiger.com" in sec_text

    # Supported versions
    assert "0.1.x" in sec_text
    assert "advisories/new" in sec_text

    # Invariants
    assert "100% Offline" in sec_text
    assert "Non-Elevation" in sec_text or "Keine Administratorrechte" in sec_text
    assert "Zero-Egress" in sec_text or "zero-egress" in sec_text


def test_ci_workflow_integrity() -> None:
    """Verify GitHub Actions CI workflows contain multi-OS testing and concurrency control."""
    ci_path = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"
    assert ci_path.is_file()
    ci_text = ci_path.read_text(encoding="utf-8")

    assert "concurrency:" in ci_text
    assert "cancel-in-progress: true" in ci_text
    assert "actions/checkout@v4" in ci_text
    assert "actions/setup-python@v5" in ci_text
    assert "ubuntu-latest" in ci_text
    assert "windows-latest" in ci_text
    assert "macos-latest" in ci_text
    assert "ruff check" in ci_text


def test_bundled_plugins_valid_json() -> None:
    """Verify all JSON plugins in plugins/ parse and define required fields."""
    plugins_dir = PROJECT_ROOT / "plugins"
    assert plugins_dir.is_dir(), "plugins/ directory not found"

    plugin_files = list(plugins_dir.glob("*.json"))
    assert len(plugin_files) >= 2, "Expected at least 2 bundled plugins"

    required_keys = {"name", "version", "extensions", "keywords", "comment_style", "auto_close_pairs"}
    for p in plugin_files:
        data = json.loads(p.read_text(encoding="utf-8"))
        missing = required_keys - set(data.keys())
        assert not missing, f"Plugin {p.name} missing keys: {missing}"
        assert isinstance(data["extensions"], list) and len(data["extensions"]) > 0
        assert isinstance(data["keywords"], list) and len(data["keywords"]) > 0
        assert isinstance(data["auto_close_pairs"], dict)


def test_welcome_and_stale_workflow_hardening() -> None:
    """Verify welcome.yml and stale.yml contain least-privilege permissions, concurrency, and timeouts."""
    welcome_path = PROJECT_ROOT / ".github" / "workflows" / "welcome.yml"
    assert welcome_path.is_file(), "welcome.yml must exist"
    welcome_text = welcome_path.read_text(encoding="utf-8")
    assert "actions/first-interaction@v3" in welcome_text
    assert "timeout-minutes: 5" in welcome_text
    assert "cancel-in-progress: true" in welcome_text
    assert "issues: write" in welcome_text
    assert "pull-requests: write" in welcome_text

    stale_path = PROJECT_ROOT / ".github" / "workflows" / "stale.yml"
    assert stale_path.is_file(), "stale.yml must exist"
    stale_text = stale_path.read_text(encoding="utf-8")
    assert "actions/stale@v9" in stale_text
    assert "timeout-minutes: 10" in stale_text
    assert "cancel-in-progress: true" in stale_text
    assert "cron: '30 1 * * *'" in stale_text
    assert "issues: write" in stale_text
    assert "pull-requests: write" in stale_text


def test_ci_and_smoke_job_timeouts() -> None:
    """Verify ci.yml and linux-platform-smoke.yml define finite job-level timeouts."""
    ci_text = (PROJECT_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "timeout-minutes: 10" in ci_text
    assert "timeout-minutes: 25" in ci_text

    smoke_text = (PROJECT_ROOT / ".github" / "workflows" / "linux-platform-smoke.yml").read_text(encoding="utf-8")
    assert "timeout-minutes: 15" in smoke_text


def test_gitignore_fleetwide_defense() -> None:
    """Verify .gitignore blocks multi-host sync conflicts, multi-agent lock files, and test caches."""
    content = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
    required_patterns = [
        "*conflicted copy*",
        "*-ASUS*",
        "*-LAPTOP*",
        "*-Mac Studio*",
        "*-MacBook*",
        "*-WORKSTATION*",
        "*-WORKSTATION-LG*",
        "LOCK.user.*",
        "LOCK.until.*",
        "LOCK.condition.*",
        ".automation-lock",
        "uv.lock",
        "!package-lock.json",
        ".pytest_temp/",
        ".hypothesis/",
        ".turbo/",
        ".tox/",
    ]
    for pat in required_patterns:
        assert pat in content, f"Missing pattern {pat} in .gitignore"


def test_changelog_and_marketing_log_recency(pyproject_data: dict) -> None:
    """Verify CHANGELOG, MARKETING-LOG, and pyproject pytest options match Pfad A 2026-09-25 baseline."""
    changelog = (PROJECT_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "Repository Hygiene, CI Lifecycle Hardening & Lock Defense (Pfad A 2026-09-25)" in changelog

    marketing = (PROJECT_ROOT / "MARKETING-LOG.txt").read_text(encoding="utf-8")
    assert "Pfad A Repository Hygiene, CI Hardening & Lock Defense - 2026-09-25" in marketing

    pytest_opts = pyproject_data.get("tool", {}).get("pytest", {}).get("ini_options", {})
    norecursedirs = pytest_opts.get("norecursedirs", [])
    assert ".pytest_temp" in norecursedirs
    assert "--basetemp=.pytest_temp" in pytest_opts.get("addopts", "")
