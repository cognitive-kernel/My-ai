# Contributing

## Development

- Python 3.11+.
- Install development dependencies with `pip install -e '.[dev]'`.
- Run `python -m compileall -q my_ai tests`.
- Run `pytest -q`.
- Run `ruff check my_ai --select F`.
- Run `mypy my_ai --ignore-missing-imports`.
- Run `bandit -r my_ai -q -lll`.
- Run `pip-audit`.

## Changes

Keep changes focused. New write/execute API routes must be registered in `my_ai/access_policy.py` and tested.
Do not commit credentials, tokens, database files, generated artifacts, or local settings keys.

## Security-sensitive changes

Changes to authentication, permissions, sandboxing, self-update, self-repair, GitHub access, or external security tooling require regression tests and a clear audit trail in the pull request.