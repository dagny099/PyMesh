#!/usr/bin/env python3
import json
import csv
import argparse
from pathlib import Path

def json_to_csv(json_path, nodes_csv_path, rels_csv_path):
    """
    Convert a dependency‐graph JSON (with `nodes` and `edges`) into two CSVs:
      - nodes_csv: id,label,type,path,module
      - rels_csv: source,target,relationship
    """
    data = json.loads(Path(json_path).read_text(encoding='utf-8'))
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])

    # Write nodes CSV
    with open(nodes_csv_path, 'w', newline='', encoding='utf-8') as nf:
        fieldnames = ["id", "label", "type", "path", "module"]
        writer = csv.DictWriter(nf, fieldnames=fieldnames)
        writer.writeheader()
        for n in nodes:
            writer.writerow({
                "id":     n.get("id", ""),
                "label":  n.get("label", ""),
                "type":   n.get("type", ""),
                "path":   n.get("path", ""),
                "module": n.get("module", "")
            })

    # Write relationships CSV
    with open(rels_csv_path, 'w', newline='', encoding='utf-8') as ef:
        fieldnames = ["source", "target", "relationship"]
        writer = csv.DictWriter(ef, fieldnames=fieldnames)
        writer.writeheader()
        for e in edges:
            writer.writerow({
                "source":       e.get("source", ""),
                "target":       e.get("target", ""),
                "relationship": e.get("relationship", "")
            })

if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description="Convert dependency‐graph JSON to Neo4j-importable CSVs"
    )
    p.add_argument("json_file", help="Path to the JSON file (e.g. dependency_graph.json)")
    p.add_argument(
        "--nodes-csv",
        default="nodes.csv",
        help="Output path for nodes CSV (default: nodes.csv)"
    )
    p.add_argument(
        "--rels-csv",
        default="relationships.csv",
        help="Output path for relationships CSV (default: relationships.csv)"
    )
    args = p.parse_args()

    json_to_csv(args.json_file, args.nodes_csv, args.rels_csv)
    print(f"✔️  Wrote nodes to {args.nodes_csv}")
    print(f"✔️  Wrote relationships to {args.rels_csv}")
