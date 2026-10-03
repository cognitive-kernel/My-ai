from pathlib import Path

from my_ai.help import DOC_FILES, DOCS_DIR, local_help


def test_all_local_help_mappings_resolve_to_existing_files():
    for component, relative_path in DOC_FILES.items():
        path = (DOCS_DIR / relative_path).resolve()
        assert path.is_file(), (component, path)


def test_relocated_security_guide_is_served():
    path = (DOCS_DIR / DOC_FILES["security"]).resolve()
    assert path == (DOCS_DIR.parent / "SECURITY.md").resolve()
    assert "# Security Policy" in local_help("security")
