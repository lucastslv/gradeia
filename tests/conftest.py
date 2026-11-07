from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def possibilidade_html() -> bytes:
    return (FIXTURES / "possibilidade_2026_2.html").read_bytes()
