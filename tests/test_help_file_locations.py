from pathlib import Path

from my_ai.help import DOC_FILES, DOC_FALLBACK_FILES, DOCS_DIR, _doc_path, local_help


def test_all_local_help_mappings_resolve_to_existing_files_or_relocated_fallbacks():
    for component in DOC_FILES:
        path = _doc_path(component).resolve()
        assert path.is_file(), (component, path)


def test_relocated_security_guide_is_served():
    path = _doc_path("security").resolve()
    assert path == (DOCS_DIR.parent / "SECURITY.md").resolve()
    assert DOC_FALLBACK_FILES["security"] == "../SECURITY.md"
    assert "# Security Policy" in local_help("security")
