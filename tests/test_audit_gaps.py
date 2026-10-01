from pathlib import Path
import io
import tokenize

from my_ai.access_policy import is_mutation, permission_for_path
from my_ai.eval_harness import DEFAULT_REGRESSION_THRESHOLDS, evaluate_regression_metrics
from my_ai.skill_engine import _verification_state


def test_sensitive_paths_have_explicit_permission_mapping():
    required = {
        ("/self-update/apply", "POST"),
        ("/self-repair/apply", "POST"),
        ("/backup/import", "POST"),
        ("/tools/python", "POST"),
        ("/skills/revalidate", "POST"),
    }
    for path, method in required:
        result = permission_for_path(path, method)
        assert result is not None
        assert result[1] in {"write", "execute"}


def test_mutating_methods_are_classified():
    assert all(is_mutation(method) for method in ("POST", "PUT", "PATCH", "DELETE"))
    assert not is_mutation("GET")


def test_regression_thresholds_cover_core_metrics():
    names = {item.name for item in DEFAULT_REGRESSION_THRESHOLDS}
    assert {"retrieval_mrr", "persian_response_mean", "citation_coverage", "confidence_calibration", "router_accuracy", "skill_verification"} <= names
    failed = evaluate_regression_metrics({name: 0.0 for name in names})
    assert failed["passed"] is False


def test_dependency_declaration_has_single_install_entrypoint():
    text = Path("requirements.txt").read_text(encoding="utf-8").strip()
    assert text == "-e ."
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    assert "[project]" in pyproject and "dependencies = [" in pyproject


def test_architecture_has_no_unresolved_placeholder_markers():
    root = Path("my_ai")
    hits = []
    for path in root.rglob("*.py"):
        source = path.read_text(encoding="utf-8-sig", errors="ignore")
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.COMMENT and any(marker in token.string for marker in ("TODO", "FIXME", "HACK", "XXX", "NotImplemented")):
                hits.append((str(path), token.start[0]))
    assert not hits, hits
