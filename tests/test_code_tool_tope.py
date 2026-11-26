import pytest
from pydantic import ValidationError

from app.tools.schema import MAX_CODE_CHARS, CodeTool


def _tool(n):
    base = "export default async function(){return 1}//"
    return CodeTool(description="d", code=base + "x" * (n - len(base)))


def test_tope_del_codigo():
    assert MAX_CODE_CHARS == 50_000
    _tool(50_000)
    with pytest.raises(ValidationError):
        _tool(50_001)
