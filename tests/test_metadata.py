"""Automated metadata, manifest, and plugin integrity test suite for CodeBox."""

import json
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
    """Ensure version parity across pyproject.toml, version.py, and CHANGELOG.md."""
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


def test_pyproject_required_fields(pyproject_data: dict) -> None:
    """Verify all expected project metadata fields exist in pyproject.toml."""
    proj = pyproject_data.get("project", {})
    assert proj.get("name") == "CodeBox"
    assert proj.get("description")
    assert proj.get("requires-python")
    assert proj.get("license", {}).get("text") == "MIT"
    assert isinstance(proj.get("authors"), list) and len(proj["authors"]) > 0
    assert isinstance(proj.get("keywords"), list) and len(proj["keywords"]) >= 5
    assert isinstance(proj.get("classifiers"), list) and len(proj["classifiers"]) >= 5

    urls = proj.get("urls", {})
    assert "Homepage" in urls
    assert "Repository" in urls
    assert "Issues" in urls


def test_core_documentation_files_exist() -> None:
    """Ensure all standard documentation and license files exist and are non-empty."""
    required_files = [
        "README.md",
        "README_de.md",
        "llms.txt",
        "CHANGELOG.md",
        "LICENSE",
        "DEVELOPMENT_PLAN.md",
        "API_STATUS.md",
    ]
    for filename in required_files:
        p = PROJECT_ROOT / filename
        assert p.is_file(), f"Missing required file: {filename}"
        assert p.stat().st_size > 0, f"File is empty: {filename}"


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
