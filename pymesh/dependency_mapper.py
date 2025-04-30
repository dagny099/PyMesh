# dependency_manager.py

import os
from typing import List, Dict, Tuple
import os
import ast
import textwrap

IGNORED_DIRS = {"__pycache__", ".git", ".venv", "venv", "env", ".env", "node_modules","old"}
IGNORED_FILES = {"__pycache__", "__init__.py"}

def extract_dependencies(file_path: str) -> Dict:
    """
    Extract all dependencies from a Python file based on import statements.
    
    Args:
        file_path: Path to the Python file
        
    Returns:
        Dictionary containing all dependencies
    """
    # Check if file exists
    if not os.path.exists(file_path):
        return {
            "error": f"File not found: {file_path}",
            "dependencies": []
        }
    
    # Read the file content
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        content = textwrap.dedent(content)  # STRIP COMMON INDENTATION

    except Exception as e:
        return {
            "error": f"Error reading file {file_path}: {str(e)}",
            "dependencies": []
        }
    
    # Parse the file using AST
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        return {
            "error": f"Syntax error in {file_path}: {str(e)}",
            "dependencies": []
        }
    
    # Extract dependencies
    dependencies = []
    
    for node in ast.walk(tree):
        # Handle 'import x' statements
        if isinstance(node, ast.Import):
            for name in node.names:
                module_name = name.name
                alias = name.asname
                
                dependencies.append({
                    "name": module_name,
                    "type": "import",
                    "alias": alias
                })
        
        # Handle 'from x import y' statements
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module if node.module else ""
            level = node.level  # For relative imports (., .., etc.)
            
            dependency = {
                "name": module_name,
                "type": "from_import",
                "imports": []
            }
            
            # Add level for relative imports
            if level > 0:
                dependency["level"] = level
            
            for name in node.names:
                item_name = name.name
                alias = name.asname
                
                dependency["imports"].append({
                    "name": item_name,
                    "alias": alias
                })
            
            dependencies.append(dependency)
    
    return {
        "file": file_path,
        "dependencies": dependencies
    }



def discover_modules(root_dir: str) -> dict:
    """
    Recursively walk through the project root and map Python module names
    to their file paths, ignoring specified directories and files.
    
    Args:
        root_dir: Path to the top-level directory of your project.
    
    Returns:
        A dict where keys are module names (dotted paths) and values are file paths.
    """
    module_map = {}
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Modify dirnames in-place to skip ignored directories
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]

        for filename in filenames:
            # Skip ignored files
            if filename in IGNORED_FILES or not filename.endswith('.py'):
                continue
            
            file_path = os.path.join(dirpath, filename)
            # Compute module name relative to root_dir
            rel_path = os.path.relpath(file_path, root_dir)
            mod_name = rel_path[:-3].replace(os.path.sep, '.')
            module_map[mod_name] = file_path

    return module_map


def resolve_file_dependencies(file_path: str, module_map: Dict[str, str], root_dir: str) -> List[str]:
    """
    Given a Python file, extract its internal dependencies and return
    the list of corresponding file paths within the project.

    Args:
        file_path: Path to the Python file to analyze.
        module_map: Mapping of module names to file paths (from discover_modules).
        root_dir: Path to the project root (to compute relative module name).

    Returns:
        A list of deduped file paths that this file depends on (internal to project).
    """
    deps_info = extract_dependencies(file_path)
    internal_files = []
    seen = set()

    # Compute current module name for resolving relative imports
    rel_curr = os.path.relpath(file_path, root_dir)[:-3].replace(os.path.sep, '.')
    
    for dep in deps_info["dependencies"]:
        # Determine the raw module string
        if dep["type"] == "import":
            mod_name = dep["name"]
        else:  # from_import
            level = dep.get("level", 0)
            base = dep["name"] or ""
            if level > 0:
                parts = rel_curr.split('.')[:-level]
                if base:
                    parts += base.split('.')
                mod_name = ".".join(parts)
            else:
                mod_name = base
        
        # If that module exists in our project, record its path (once)
        path = module_map.get(mod_name)
        if path and path not in seen:
            seen.add(path)
            internal_files.append(path)
    
    # Debug output
    print(f"\nFile: {file_path}")
    print(f"  Resolved internal modules: {len(internal_files)}")
    for p in internal_files:
        print(f"    - {p}")
    
    return internal_files

# Recursive driver to build full dependency graph
def build_dependency_graph(entry_file: str, module_map: Dict[str, str], root_dir: str) -> Dict[str, List[str]]:
    """
    Walks dependencies starting from entry_file, recursively resolving
    each file's internal dependencies to build the full graph.
    """
    graph = {}
    visited = set()

    def dfs(file_path: str):
        if file_path in visited:
            return
        visited.add(file_path)
        deps = resolve_file_dependencies(file_path, module_map, root_dir)
        graph[file_path] = deps
        for dep_path in deps:
            dfs(dep_path)

    dfs(entry_file)
    return graph


def export_graph_to_json(graph: Dict[str, List[str]], root_dir: str, output_file: str = 'dependency_graph.json') -> None:
    """
    Export the dependency graph to a JSON file, using paths relative to the project root.
    
    Args:
        graph: Dependency graph mapping file paths to dependent file paths.
        root_dir: Project root directory for making paths relative.
        output_file: Name of the JSON file to write.
    """
    graph_rel = {}
    for file_path, deps in graph.items():
        # Convert absolute paths to paths relative to root
        rel_file = os.path.relpath(file_path, root_dir)
        # Convert each dependency path as well
        rel_deps = [os.path.relpath(dep, root_dir) for dep in deps]
        graph_rel[rel_file] = rel_deps

    # Write out JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(graph_rel, f, indent=2)

    # Debug/confirmation output
    print(f"Exported dependency graph with {len(graph_rel)} nodes to {output_file}")


def extract_defined_functions(file_path: str) -> list:
    """
    Extract all top-level function names from a Python file using AST.

    Args:
        file_path: Path to the Python file.

    Returns:
        A list of function names defined in the file.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        content = textwrap.dedent(content)  # strip any common leading whitespace so AST won't choke on indents
    except Exception as e:
        print(f"Could not read {file_path}: {e}")
        return []
    
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        print(f"Syntax error in {file_path}: {e}")
        return []

    functions = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # Collect the function name
            functions.append(node.name)
    return functions

def resolve_function_usages( file_path: str, module_map: Dict[str, str], root_dir: str, module_functions: Dict[str, List[str]]) -> List[Dict[str, str]]:
    """
    For a given Python file, find which functions from other modules are actually called.
    
    Args:
        file_path: Path to the Python file.
        module_map: Mapping of module names -> file paths.
        root_dir: Project root for relative resolution.
        module_functions: Mapping of module names -> list of defined function names.
    
    Returns:
        A list of dicts: { module: str, function: str, path: str } for each used function.
    """
    # Read and parse the file
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return []

    # Build import alias maps
    alias_map: Dict[str, str] = {}         # e.g. { 'tc': 'src.timeline_components' }
    direct_imports: Dict[str, Tuple[str, str]] = {}  # e.g. { 'initialize_session_state': ('src.timeline_components','initialize_session_state') }

    rel_curr = os.path.relpath(file_path, root_dir)[:-3].replace(os.path.sep, '.')

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                alias = name.asname or name.name.split('.')[0]
                alias_map[alias] = name.name  # full module path as imported

        elif isinstance(node, ast.ImportFrom):
            level = node.level
            base = node.module or ""
            # Resolve relative module if needed
            if level > 0:
                parts = rel_curr.split('.')[:-level]
                if base:
                    parts += base.split('.')
                base = ".".join(parts)
            for name in node.names:
                fn_alias = name.asname or name.name
                direct_imports[fn_alias] = (base, name.name)

    # Scan for function calls
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            # Case: direct call to imported fn
            if isinstance(func, ast.Name) and func.id in direct_imports:
                calls.add(direct_imports[func.id])
            # Case: module.fn()
            elif isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                mod_alias = func.value.id
                if mod_alias in alias_map:
                    calls.add((alias_map[mod_alias], func.attr))

    # Map to project paths and drop any not in our definitions
    resolved = []
    for mod, fn in calls:
        if mod in module_map and fn in module_functions.get(mod, []):
            resolved.append({ "module": mod, "function": fn, "path": module_map[mod] })

    # Debug output
    print(f"\nFile: {file_path}")
    print("  Functions called:")
    for d in resolved:
        print(f"    - {d['module']}.{d['function']} ({d['path']})")
    return resolved


def build_function_dependency_graph(entry_file: str, module_map: Dict[str, str], root_dir: str, module_functions: Dict[str, List[str]]) -> Dict[str, List[Dict[str, str]]]:
    """
    Recursively walk from entry_file, resolving and recording actual function calls
    between modules.

    Returns:
        A dict mapping each file to a list of usage dicts:
        { "module": <module_name>, "function": <fn_name>, "path": <file_path> }
    """
    func_graph = {}
    visited = set()

    def dfs(file_path: str):
        if file_path in visited:
            return
        visited.add(file_path)

        # Find functions this file calls
        usages = resolve_function_usages(
            file_path, module_map, root_dir, module_functions
        )
        func_graph[file_path] = usages

        # Recurse into each called module
        for usage in usages:
            dfs(usage["path"])

    dfs(entry_file)
    return func_graph
