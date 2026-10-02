from __future__ import annotations

import subprocess
import sys
from pathlib import Path

DEFAULT_FILE_TIMEOUT_SECONDS = 30


def run_test_suite(root: Path, *, per_file_timeout: int = DEFAULT_FILE_TIMEOUT_SECONDS) -> tuple[bool, str]:
    root = Path(root)
    compile_run = subprocess.run(
        [sys.executable, "-m", "compileall", "-q", "my_ai", "tests"],
        cwd=root,
        text=True,
        capture_output=True,
        timeout=per_file_timeout,
    )
    if compile_run.returncode:
        return False, "compileall failed:\n" + (compile_run.stdout + compile_run.stderr).strip()

    tests_dir = root / "tests"
    if not tests_dir.exists():
        return True, "compileall passed; no tests directory present"

    files = sorted(tests_dir.rglob("test_*.py"))
    for test_file in files:
        try:
            run = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", str(test_file.relative_to(root))],
                cwd=root,
                text=True,
                capture_output=True,
                timeout=per_file_timeout,
            )
        except subprocess.TimeoutExpired as exc:
            return False, f"pytest timeout ({per_file_timeout}s): {test_file}\\n{exc.stdout!r}\\n{exc.stderr!r}"
        if run.returncode:
            return False, f"pytest failed: {test_file}\n{run.stdout}{run.stderr}".strip()
    return True, f"compileall + {len(files)} test files passed (timeout={per_file_timeout}s/file)"
