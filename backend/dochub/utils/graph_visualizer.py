# backend/dochub/utils/graph_visualizer.py

import os
import json
import logging
from pathlib import Path
from django.conf import settings

logger = logging.getLogger(__name__)

def generate_graph_html(entities, relationships, output_path):
    """
    Generate an HTML file to visualize the knowledge graph using vis.js
    
    Args:
        entities: List of entity dictionaries
        relationships: List of relationship dictionaries
        output_path: Path to save the HTML file
        
    Returns:
        str: Path to the generated HTML file
    """
    try:
        # Prepare nodes
        nodes = []
        for i, entity in enumerate(entities):
            entity_type = entity.get('type', 'Unknown')
            color = get_entity_color(entity_type)
            
            nodes.append({
                'id': i,
                'label': entity.get('name', f"Entity {i}"),
                'title': f"Type: {entity_type}<br>Properties: {json.dumps(entity)}",
                'color': color,
                'group': entity_type
            })
        
        # Prepare edges
        edges = []
        for i, rel in enumerate(relationships):
            # Find source and target nodes
            source_name = rel.get('source')
            target_name = rel.get('target')
            
            source_index = next((i for i, e in enumerate(entities) if e.get('name') == source_name), None)
            target_index = next((i for i, e in enumerate(entities) if e.get('name') == target_name), None)
            
            if source_index is not None and target_index is not None:
                edges.append({
                    'from': source_index,
                    'to': target_index,
                    'label': rel.get('relation', 'RELATED_TO'),
                    'arrows': 'to',
                    'title': json.dumps(rel)
                })
        
        # Generate HTML
        html = generate_vis_html(nodes, edges)
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        logger.info(f"Generated graph visualization at {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Error generating graph visualization: {str(e)}")
        return None

def get_entity_color(entity_type):
    """Get a color for an entity type"""
    color_map = {
        'Person': '#4285F4',        # Google Blue
        'Organization': '#34A853',  # Google Green
        'Location': '#FBBC05',      # Google Yellow
        'Concept': '#EA4335',       # Google Red
        'DateTime': '#9C27B0',      # Purple
        'Case': '#03A9F4',          # Light Blue
        'Court': '#795548',         # Brown
        'Judge': '#607D8B',         # Blue Grey
        'Statute': '#FF9800',       # Orange
        'Party': '#8BC34A',         # Light Green
        'Entity': '#9E9E9E',        # Grey
    }
    
    return color_map.get(entity_type, '#9E9E9E')  # Default to grey

def generate_vis_html(nodes, edges):
    """Generate HTML with vis.js for graph visualization"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Knowledge Graph Visualization</title>
        <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
        <style type="text/css">
            #graph {{
                width: 100%;
                height: 800px;
                border: 1px solid lightgray;
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                margin: 0;
                padding: 20px;
            }}
            .controls {{
                margin-bottom: 20px;
            }}
            h1 {{
                color: #333;
            }}
            .info {{
                margin-top: 20px;
                padding: 10px;
                background-color: #f5f5f5;
                border-radius: 5px;
            }}
        </style>
    </head>
    <body>
        <h1>Knowledge Graph Visualization</h1>
        
        <div class="controls">
            <button onclick="expandAll()">Expand All</button>
            <button onclick="collapseAll()">Collapse All</button>
            <input type="range" min="0.1" max="5" step="0.1" value="1" id="zoomSlider" onchange="setZoom()">
            <label for="zoomSlider">Zoom</label>
        </div>
        
        <div id="graph"></div>
        
        <div class="info">
            <p><strong>Nodes:</strong> {len(nodes)}</p>
            <p><strong>Edges:</strong> {len(edges)}</p>
            <p>Click on nodes or edges to see more details.</p>
        </div>
        
        <script type="text/javascript">
            // Create a network
            var container = document.getElementById('graph');
            
            var data = {{
                nodes: new vis.DataSet({json.dumps(nodes)}),
                edges: new vis.DataSet({json.dumps(edges)})
            }};
            
            var options = {{
                nodes: {{
                    shape: 'dot',
                    size: 16,
                    font: {{
                        size: 14
                    }},
                    borderWidth: 2,
                    shadow: true
                }},
                edges: {{
                    width: 2,
                    shadow: true,
                    font: {{
                        size: 12,
                        align: 'middle'
                    }}
                }},
                physics: {{
                    enabled: true,
                    barnesHut: {{
                        gravitationalConstant: -2000,
                        centralGravity: 0.1,
                        springLength: 150,
                        springConstant: 0.04,
                        damping: 0.09
                    }}
                }},
                interaction: {{
                    tooltipDelay: 200,
                    hover: true,
                    zoomView: true
                }}
            }};
            
            var network = new vis.Network(container, data, options);
            
            // Helper functions
            function expandAll() {{
                options.physics.enabled = true;
                network.setOptions(options);
            }}
            
            function collapseAll() {{
                options.physics.enabled = false;
                network.setOptions(options);
            }}
            
            function setZoom() {{
                var zoomLevel = document.getElementById('zoomSlider').value;
                network.moveTo({{
                    scale: parseFloat(zoomLevel)
                }});
            }}
            
            // Add event listeners
            network.on("doubleClick", function(params) {{
                if (params.nodes.length > 0) {{
                    // Find connected nodes and highlight them
                    var nodeId = params.nodes[0];
                    var connectedNodes = network.getConnectedNodes(nodeId);
                    var allNodes = data.nodes.get({{returnType: "Object"}});
                    var allEdges = data.edges.get({{returnType: "Object"}});
                    
                    // Reset all node colors
                    for (var i in allNodes) {{
                        allNodes[i].color = allNodes[i].originalColor || allNodes[i].color;
                    }}
                    
                    // Highlight selected node and its connections
                    allNodes[nodeId].color = '#FF5722';
                    for (var i = 0; i < connectedNodes.length; i++) {{
                        allNodes[connectedNodes[i]].color = '#8BC34A';
                    }}
                    
                    data.nodes.update(Object.values(allNodes));
                }}
            }});
        </script>
    </body>
    </html>
    """

def visualize_graph_from_json(json_path, output_dir=None):
    """
    Create a visualization from a saved graph JSON file
    
    Args:
        json_path: Path to the graph JSON file
        output_dir: Directory to save the visualization (default: same as JSON)
        
    Returns:
        str: Path to the generated HTML file
    """
    try:
        # Load JSON data
        with open(json_path, 'r', encoding='utf-8') as f:
            graph_data = json.load(f)
        
        entities = graph_data.get('entities', [])
        relationships = graph_data.get('relationships', [])
        
        # Determine output path
        if output_dir is None:
            output_dir = os.path.dirname(json_path)
        
        base_name = os.path.splitext(os.path.basename(json_path))[0]
        output_path = os.path.join(output_dir, f"{base_name}_visualization.html")
        
        # Generate visualization
        return generate_graph_html(entities, relationships, output_path)
    
    except Exception as e:
        logger.error(f"Error visualizing graph from JSON: {str(e)}")
        return None

def visualize_test_graph(document_id):
    """
    Visualize a graph from a pipeline test
    
    Args:
        document_id: ID of the document
        
    Returns:
        str: Path to the generated HTML file
    """
    try:
        # Find the graph data JSON
        artifact_dir = Path(settings.MEDIA_ROOT) / 'pipeline_tests' / document_id
        graph_json = artifact_dir / 'graph_data.json'
        
        if not graph_json.exists():
            logger.error(f"Graph data not found for document {document_id}")
            return None
        
        # Generate visualization
        output_path = artifact_dir / 'graph_visualization.html'
        return visualize_graph_from_json(graph_json, artifact_dir)
        
    except Exception as e:
        logger.error(f"Error visualizing test graph: {str(e)}")
        return None