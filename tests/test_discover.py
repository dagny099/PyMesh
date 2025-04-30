import os
from pathlib import Path
import pytest
from utils.dependency_mapper import discover_modules

def test_discover_modules(tmp_path):
    # Create a sample Python file structure
    project = tmp_path / "proj"
    src = project / "src"
    src.mkdir(parents=True)
    file_a = src / "a.py"
    file_b = src / "b.py"
    file_a.write_text("# sample a")
    file_b.write_text("# sample b")

    result = discover_modules(str(project))
    # Expect module names without .py
    expected = {"src.a", "src.b"}
    assert set(result.keys()) == expected