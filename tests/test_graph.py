import pytest
from pymesh.dependency_mapper import ( build_dependency_graph, build_function_dependency_graph, discover_modules, extract_defined_functions)
from pathlib import Path

def test_build_graph_simple(tmp_path):
    # Create two files: a.py imports b.py
    proj = tmp_path / "proj2"
    src = proj / "src"
    src.mkdir(parents=True)
    a = src / "app.py"
    b = src / "b.py"
    a.write_text("import src.b")
    b.write_text("def func(): pass")

    modules = discover_modules(str(proj))
    module_funcs = {m: extract_defined_functions(p) for m, p in modules.items()}
    graph = build_dependency_graph(str(a), modules, str(proj))
    assert str(b) in graph[str(a)]

    func_graph = build_function_dependency_graph(str(a), modules, str(proj), module_funcs)
    # No calls, so empty
    assert func_graph[str(a)] == []