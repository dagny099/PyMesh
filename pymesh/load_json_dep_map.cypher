CALL apoc.load.json("https://raw.githubusercontent.com/dagny099/dagny099.github.io/refs/heads/master/assets/docs/dependency-mapping-tool_dependency_graph.json")
YIELD value
// UNWIND nodes and create/merge them
UNWIND value.nodes AS node
CALL apoc.merge.node(
  [ node.type ],        // labels: Module or Function
  { id: node.id },      // merge key
  node                  // all other properties
) YIELD node AS createdNode

// Now UNWIND edges and create/merge those
UNWIND value.edges AS rel
MATCH (src { id: rel.source }), (tgt { id: rel.target })
CALL apoc.merge.relationship(
  src,
  rel.relationship,  // "defines" or "calls"
  {}, 
  {},
  tgt
) YIELD rel AS createdRel

RETURN 
  count(DISTINCT createdNode) AS nodesImported,
  count(createdRel)           AS relationshipsImported;

  // SAMPLE QUERY: MATCH (f:function)-[r]->(m:module) RETURN f, r, m;
