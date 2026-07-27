from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_public_docs_do_not_advertise_unimplemented_remote_api():
    for name in ("README.md", "README_de.md"):
        text = (PROJECT_ROOT / name).read_text(encoding="utf-8")
        assert "REST API and CLI foundation" not in text
        assert "REST-API-/CLI-Grundlage" not in text


def test_api_status_documents_only_the_supported_local_cli():
    text = (PROJECT_ROOT / "API_STATUS.md").read_text(encoding="utf-8")
    assert "python main.py --open <datei>" in text
    assert "keine REST-Routen" in text
    assert "keine OpenAPI-/Swagger-Spezifikation" in text
