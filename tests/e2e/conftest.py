from __future__ import annotations

import os

import pytest


@pytest.fixture
def base_url() -> str:
    return os.getenv("BASE_URL", "http://127.0.0.1:8000")
