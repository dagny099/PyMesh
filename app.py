import streamlit as st
import os
from pathlib import Path
import streamlit.components.v1 as components
from pyvis.network import Network
import json
from datetime import datetime

# Import your dependency-mapper utilities
from utils.dependency_mapper import (
    discover_modules,
    extract_defined_functions,
    build_function_dependency_graph,
)
import style_config as style

# Page configuration
st.set_page_config(
    page_title=style.TITLE,
    page_icon="🧭",
    layout="wide",
    # initial_sidebar_state="expanded"
    )

def main():
    st.title(style.TITLE)
    st.markdown(style.DESCRIPTION)

    # Step 1: Specify project directory
    project_dir = st.text_input(
        label=style.DIR_INPUT_LABEL,
        value=str(Path.cwd())
    )
    if not os.path.isdir(project_dir):
        st.error(f"Directory not found: {project_dir}")
        return
    project_name = Path(project_dir).name

    # Sidebar: Output settings
    st.sidebar.header("Output Settings")
    html_file_name = st.sidebar.text_input(
        "HTML file name:",
        value=f"{project_name}_dependency_map.html"
    )
    json_file_name = st.sidebar.text_input(
        "JSON file name:",
        value=f"{project_name}_dependency_graph.json"
    )
    save_outputs = st.sidebar.checkbox(
        "Save outputs to project directory",
        value=False
    )

    # Step 2: Scan for modules
    if st.button(style.SCAN_BUTTON_LABEL):
        modules = discover_modules(project_dir)
        st.session_state['modules'] = modules
        module_funcs = {m: extract_defined_functions(p) for m, p in modules.items()}
        st.session_state['module_functions'] = module_funcs
    modules = st.session_state.get('modules', {})
    module_funcs = st.session_state.get('module_functions', {})
    module_list = sorted(modules.keys())

    # Sidebar: Entry-point selection and visibility toggles
    st.sidebar.header(style.SIDEBAR_ENTRY_HEADER)
    entry_points = st.sidebar.multiselect(
        label=style.MULTISELECT_LABEL,
        options=module_list,
        default=[]
    )
    st.session_state['entries'] = entry_points

    st.sidebar.header(style.CHECKBOX_SECTION_TITLE)
    visible_modules = []
    for mod in module_list:
        if st.sidebar.checkbox(f"Show {mod}", value=True, key=f"show_{mod}"):
            visible_modules.append(mod)

    # Step 3: Visualization
    if entry_points:
        # Prepare combined function-level graph data
        combined_graph = {}
        for ep in entry_points:
            ep_path = os.path.join(project_dir, ep.replace('.', os.sep) + '.py')
            func_graph = build_function_dependency_graph(
                ep_path, modules, project_dir, module_funcs
            )
            combined_graph[ep] = func_graph

        # Initialize PyVis network
        net = Network(notebook=True, height="600px", width="100%")

        # Add nodes and edges to PyVis
        for module, funcs in module_funcs.items():
            if module not in visible_modules:
                continue
            shape = "star" if module in entry_points else "box"
            color = "gold" if module in entry_points else "skyblue"
            net.add_node(module, label=module, shape=shape, color=color)
            for fn in funcs:
                fn_node = f"{module}.{fn}"
                net.add_node(fn_node, label=fn, shape="ellipse", color="lightgreen")
                net.add_edge(module, fn_node, 
                             title="defines",
                             color="gray",
                             width=2,
                             arrows="to",
                             dash=False)
        for ep, func_graph in combined_graph.items():
            for caller_path, usages in func_graph.items():
                caller_mod = os.path.relpath(caller_path, project_dir)[:-3].replace(os.path.sep, '.')
                if caller_mod not in visible_modules:
                    continue
                for u in usages:
                    mod = u['module']
                    if mod not in visible_modules:
                        continue
                    fn_node = f"{mod}.{u['function']}"
                    net.add_edge(caller_mod, fn_node, 
                                 title="calls",
                                 color="yellow",
                                 width=4,
                                 arrows="to",
                                 dash=True)

        # Graph title, path, and timestamp
        graph_title = f"{project_name} Dependency Graph"
        project_path_html = f"Project Directory: {project_dir}"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Ensure output directory exists
        output_dir = Path(project_dir) / "dependency_mapper_outputs"
        output_dir.mkdir(exist_ok=True)

        # Save HTML
        html_path = output_dir / html_file_name
        net.show(str(html_path))

        # Inject header info into HTML
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        insert_html = (
            f"<h1 style='text-align:center;'>{graph_title}</h1>"
            f"<p style='text-align:center;font-size:0.9em;color:gray;'>{project_path_html}</p>"
            f"<p style='text-align:center;font-size:0.9em;color:gray;'>Generated on {timestamp}</p>"
        )
        html_content = html_content.replace("<body>", f"<body>\n{insert_html}")
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        # Display interactive HTML
        components.html(html_content, height=650)

        # Step 4: Save enriched JSON if requested
        if save_outputs:
            json_path = output_dir / json_file_name
            # Build enriched JSON export
            nodes = []
            edges = []
            # Nodes: modules
            for module, funcs in module_funcs.items():
                if module not in visible_modules:
                    continue
                nodes.append({
                    "id": module,
                    "label": module,
                    "type": "module",
                    "path": modules[module]
                })
                for fn in funcs:
                    fn_node = f"{module}.{fn}"
                    nodes.append({
                        "id": fn_node,
                        "label": fn,
                        "type": "function",
                        "module": module,
                        "path": modules[module]
                    })
                    edges.append({
                        "source": module,
                        "target": fn_node,
                        "relationship": "defines"
                    })
            # Edges: calls
            for ep, func_graph in combined_graph.items():
                for caller_path, usages in func_graph.items():
                    caller_mod = os.path.relpath(caller_path, project_dir)[:-3].replace(os.path.sep, '.')
                    if caller_mod not in visible_modules:
                        continue
                    for u in usages:
                        mod = u['module']
                        if mod not in visible_modules:
                            continue
                        fn_node = f"{mod}.{u['function']}"
                        edges.append({
                            "source": caller_mod,
                            "target": fn_node,
                            "relationship": "calls"
                        })
            export_data = { "nodes": nodes, "edges": edges }
            with open(json_path, 'w', encoding='utf-8') as jf:
                json.dump(export_data, jf, indent=2)

            st.success(f"Saved HTML to {html_path} and JSON to {json_path}")

if __name__ == "__main__":
    main()