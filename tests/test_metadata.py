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
    assert "Last-checked: 2026-08-24" in llms_text


def test_pyproject_required_fields(pyproject_data: dict) -> None:
    """Verify all expected project metadata fields exist in pyproject.toml."""
    proj = pyproject_data.get("project", {})
    assert proj.get("name") == "CodeBox"
    assert proj.get("description")
    assert proj.get("requires-python")
    assert proj.get("license", {}).get("text") == "MIT"
    assert isinstance(proj.get("authors"), list) and len(proj["authors"]) > 0
    assert isinstance(proj.get("keywords"), list) and len(proj["keywords"]) >= 5
    assert isinstance(proj.get("classifiers"), list) and len(proj["classifiers"]) >= 10

    urls = proj.get("urls", {})
    assert "Homepage" in urls
    assert "Repository" in urls
    assert "Issues" in urls
    assert "Changelog" in urls
    assert "Security" in urls
    assert "Parent Org" in urls
    assert "Umbrella Ecosystem" in urls


def test_core_documentation_files_exist() -> None:
    """Ensure all standard documentation and license files exist and are non-empty."""
    required_files = [
        "README.md",
        "README_de.md",
        "llms.txt",
        "CHANGELOG.md",
        "LICENSE",
        "SECURITY.md",
        "DEVELOPMENT_PLAN.md",
        "API_STATUS.md",
    ]
    for filename in required_files:
        p = PROJECT_ROOT / filename
        assert p.is_file(), f"Missing required file: {filename}"
        assert p.stat().st_size > 0, f"File is empty: {filename}"


def test_bilingual_readme_parity_and_anchors() -> None:
    """Ensure English and German READMEs have corresponding headers, anchors, and badges."""
    readme_en = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    readme_de = (PROJECT_ROOT / "README_de.md").read_text(encoding="utf-8")

    # Both must cross-link
    assert "[Deutsch](README_de.md)" in readme_en
    assert "[English](README.md)" in readme_de

    # Check key badges
    for text in [readme_en, readme_de]:
        assert "img.shields.io/badge/License-MIT" in text or "img.shields.io/badge/Lizenz-MIT" in text
        assert "ecosystem-dev--bricks" in text
        assert "part%20of-open--bricks" in text
        assert "tests-120%20passed" in text
        assert "llms.txt" in text
        assert "SECURITY.md" in text

    # Check quick navigation section
    assert "## Quick Navigation" in readme_en
    assert "## Schnellnavigation" in readme_de


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
