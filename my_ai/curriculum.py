from __future__ import annotations

PYTHON_CURRICULUM: list[dict[str, object]] = [
    {"order": 1, "topic": "Syntax and execution", "goal": "Run scripts, understand indentation, comments, expressions."},
    {"order": 2, "topic": "Variables and types", "goal": "Use numbers, strings, booleans, None, conversions."},
    {"order": 3, "topic": "Control flow", "goal": "Use if, for, while, match, break, continue."},
    {"order": 4, "topic": "Functions", "goal": "Define functions, parameters, returns, scope and decorators."},
    {"order": 5, "topic": "Collections", "goal": "Master list, tuple, set, dict and comprehensions."},
    {"order": 6, "topic": "Modules and packages", "goal": "Import modules, structure packages and manage dependencies."},
    {"order": 7, "topic": "Exceptions", "goal": "Design robust exception handling and custom exceptions."},
    {"order": 8, "topic": "Files and serialization", "goal": "Work with files, JSON, CSV and paths."},
    {"order": 9, "topic": "Object-oriented Python", "goal": "Use classes, inheritance, composition and protocols."},
    {"order": 10, "topic": "Typing", "goal": "Use type hints, generics, protocols and static analysis concepts."},
    {"order": 11, "topic": "Testing", "goal": "Write unit tests, fixtures and regression tests."},
    {"order": 12, "topic": "Async programming", "goal": "Understand async/await, tasks and concurrency."},
    {"order": 13, "topic": "Databases", "goal": "Use SQLite, SQL and data-access patterns."},
    {"order": 14, "topic": "HTTP and APIs", "goal": "Build and consume HTTP APIs with FastAPI and httpx."},
    {"order": 15, "topic": "Packaging", "goal": "Build installable packages and reproducible environments."},
    {"order": 16, "topic": "Production practices", "goal": "Logging, configuration, security, performance and deployment."},
]


def next_topic(completed: set[str] | None = None) -> dict[str, object] | None:
    completed = completed or set()
    for item in PYTHON_CURRICULUM:
        if str(item["topic"]) not in completed:
            return item
    return None
