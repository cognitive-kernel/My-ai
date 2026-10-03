from pathlib import Path

import pytest

pytestmark = pytest.mark.timeout(30)


def test_chat_api_invokes_registered_market_quote_capability():
    source = Path("my_ai/api.py").read_text(encoding="utf-8")
    assert 'if capability == "market.quote":' in source
    assert "mt4_quote(symbol)" in source
    assert '"type":"market_quote"' in source
    assert "_persist_api_chat_turn(sid, msg, answer)" in source
