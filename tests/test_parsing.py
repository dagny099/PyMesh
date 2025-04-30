import pytest
from utils.dependency_mapper import extract_defined_functions, extract_dependencies
from pathlib import Path

def test_extract_defined_functions(tmp_path):
    f = tmp_path / "mod.py"
    f.write_text(
        """
        def foo(): pass
        def bar(x, y): return x + y
        """
    )
    funcs = extract_defined_functions(str(f))
    assert set(funcs) == {"foo", "bar"}


def test_extract_dependencies(tmp_path):
    f = tmp_path / "mod2.py"
    f.write_text(
        """
        import os
        from math import sqrt, sin as sine
        from .helper import util
        """
    )
    deps = extract_dependencies(str(f))
    names = [d["name"] for d in deps["dependencies"]]
    assert "os" in names
    assert any(d["name"] == "math" for d in deps["dependencies"])
    assert any(d.get("level", 0) == 1 for d in deps["dependencies"])