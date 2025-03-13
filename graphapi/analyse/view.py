from rest_framework.decorators import api_view
from rest_framework.response import Response
# from utility import *



from graphapi.utility import run_query
from django.http import JsonResponse

@api_view(['POST'])
def Node_clasification(request):
    # Split the query into individual statements
    queries = [
        """
        // Part 1: Create contactWithPhone relationships
        MATCH (p1:Personne)-[:Proprietaire]-(ph1:Phone)-[ap:Appel_telephone]->(ph2:Phone)-[:Proprietaire]-(p2:Personne)
        WHERE p1 <> p2
        WITH p1, p2, ap.duree_sec AS call_duration
        ORDER BY p1.identity, p2.identity
        WITH p1, p2, 
             SUM(call_duration) AS total_call_duration, 
             COUNT(*) AS call_count
        MERGE (p1)-[e:contactWithPhone]->(p2)
        SET e.total_call_duration = total_call_duration,
            e.call_count = call_count;
        """,
        """
        // Part 2: Calculate Lvl_of_Implications for each Personne node
        MATCH (p:Personne)
        OPTIONAL MATCH (p)-[r:Impliquer]-(:Affaire)  
        WITH p, COUNT(r) AS num_affaires_LvL0

        OPTIONAL MATCH (p)-[:contactWithPhone]-(p1:Personne)-[r1:Impliquer]-(:Affaire)
        WITH p, num_affaires_LvL0, COUNT(r1) AS num_affaires_LvL1

        OPTIONAL MATCH (p)-[:contactWithPhone]-(p1:Personne)
                      -[:contactWithPhone]-(p2:Personne)
                      -[r2:Impliquer]-(:Affaire)
        WITH p, num_affaires_LvL0, num_affaires_LvL1, COUNT(r2) AS num_affaires_LvL2

        OPTIONAL MATCH (p)-[:contactWithPhone]-(p1:Personne)
                      -[:contactWithPhone]-(p2:Personne)
                      -[:contactWithPhone]-(p3:Personne)
                      -[r3:Impliquer]-(:Affaire)
        WITH p, num_affaires_LvL0, num_affaires_LvL1, num_affaires_LvL2, COUNT(r3) AS num_affaires_LvL3

        OPTIONAL MATCH (p)-[:contactWithPhone]-(p1:Personne)
                      -[:contactWithPhone]-(p2:Personne)
                      -[:contactWithPhone]-(p3:Personne)
                      -[:contactWithPhone]-(p4:Personne)
                      -[r4:Impliquer]-(:Affaire)
        WITH p, num_affaires_LvL0, num_affaires_LvL1, num_affaires_LvL2, num_affaires_LvL3, COUNT(r4) AS num_affaires_LvL4

        SET p.Lvl_of_Implications = [num_affaires_LvL0, num_affaires_LvL1, num_affaires_LvL2, num_affaires_LvL3, num_affaires_LvL4];
        """,
        """
        // Part 3: Initialize properties for all Personne nodes
        MATCH (p:Personne)
        SET p.class = ["neutre"],
            p.affireOpretioneele = [],
            p.affiresoutin = [],
            p.affireleader = [];
        """,
        """
        // Part 4: Assign "operationeel" to Personne nodes with Lvl_of_Implications[0] > 0
        MATCH (p:Personne)
        WHERE "neutre" IN p.class AND p.Lvl_of_Implications[0] > 0
        SET p.class = p.class + "operationeel"
        WITH p
        MATCH (p)-[:Impliquer]-(a:Affaire)
        WITH p, COLLECT(a.identity) AS affaire_ids
        SET p.affireOpretioneele = affaire_ids;
        """,
        """
        // Part 5: Assign "soutien" to Personne nodes connected to "operationeel" nodes
        MATCH (p1:Personne)-[:contactWithPhone]-(p2:Personne)
        WHERE "operationeel" IN p1.class AND p2.Lvl_of_Implications[1] > p1.Lvl_of_Implications[0]
        SET p2.class = CASE WHEN NOT "soutien" IN p2.class THEN p2.class + "soutien" ELSE p2.class END,
            p2.affiresoutin = p2.affiresoutin + p1.affireOpretioneele;
        """,
        """
        WITH range(1, 1) AS levels
        UNWIND levels AS i
        MATCH (p1:Personne)-[:contactWithPhone]-(p2:Personne)
        WHERE "soutien" IN p1.class AND p2.Lvl_of_Implications[i+1] > p1.Lvl_of_Implications[i]
        SET p2.class = CASE WHEN NOT "soutien" IN p2.class THEN p2.class + "soutien" ELSE p2.class END,
            p2.affiresoutin = p2.affiresoutin + p1.affiresoutin;
        """,
        """
        // Part 6: Assign "leader" to Personne nodes that qualify
        WITH range(1, 1) AS leader_levels
        UNWIND leader_levels AS i
        MATCH (p1:Personne)
        WHERE "soutien" IN p1.class
        WITH p1, i,
             ALL(p2 IN [(p1)-[:contactWithPhone]-(p2:Personne) | p2] 
                 WHERE p2.Lvl_of_Implications[i] < p1.Lvl_of_Implications[i+1]) AS level_leader
        WITH p1, COLLECT(level_leader) AS leader_flags
        WHERE ANY(flag IN leader_flags WHERE flag = true)
        SET p1.class = CASE WHEN NOT "leader" IN p1.class THEN p1.class + "leader" ELSE p1.class END,
            p1.affireleader = p1.affiresoutin;
        """,
        """
        // Part 7: Delete all contactWithPhone relationships
        MATCH (p1:Personne)-[r:contactWithPhone]-(p2:Personne)
        DELETE r;
        """
    ]

    # Execute each query sequentially
    results = []
    for query in queries:
        data = run_query(query)
        results.append(data)

    # Return the result as a JSON response
    return JsonResponse(results, safe=False)





@api_view(['POST'])
def calculate_degree_centrality(request):
    relationships = request.data
    if not relationships:
        return Response({"error": "No relationships provided."}, status=400)
    
    nodes = set()
    edges = []

    if not isinstance(relationships, list):
        return Response({"error": "Invalid input format. Expected a list of relationships."}, status=400)
    
    for rel in relationships:
        if not all(key in rel for key in ['from', 'to', 'label']):
            return Response({"error": "Invalid relationship format. Each relationship must include 'from', 'to', and 'label'."}, status=400)
        
        from_node, to_node, label = rel['from'], rel['to'], rel['label']
        nodes.add(from_node)
        nodes.add(to_node)
        edges.append({"start": from_node, "end": to_node, "type": label})
    
    gds_graph_name = "tempSubgraph"

    try:
        create_nodes_query = """
        UNWIND $nodes AS node_id
        MERGE (n:TempNode {id: node_id})
        """
        create_edges_query = """
        UNWIND $edges AS edge
        MATCH (start:TempNode {id: edge.start}), (end:TempNode {id: edge.end})
        MERGE (start)-[r:TempRel {type: edge.type}]->(end)
        """
        create_gds_graph_query = f"""
        CALL gds.graph.project(
            '{gds_graph_name}',
            'TempNode',
            {{
                TempRel: {{
                    orientation: 'Undirected'
                }}
            }}
        )
        """

        run_query(create_nodes_query, {"nodes": list(nodes)})
        run_query(create_edges_query, {"edges": edges})
        run_query(create_gds_graph_query, {})

        centrality_query = f"""
        CALL gds.eigenvector.stream('{gds_graph_name}')
        YIELD nodeId, score
        RETURN gds.util.asNode(nodeId).id AS node_id, score
        ORDER BY score DESC
        """
        centrality_results = run_query(centrality_query)

        cleanup_query = f"CALL gds.graph.drop('{gds_graph_name}') YIELD graphName"
        delete_temp_nodes = "MATCH (n:TempNode) DETACH DELETE n"
        run_query(cleanup_query)
        run_query(delete_temp_nodes)

        return Response({"degree_centrality": centrality_results}, status=200)
    
    except Exception as e:
        cleanup_query = f"CALL gds.graph.drop('{gds_graph_name}') YIELD graphName"
        delete_temp_nodes = "MATCH (n:TempNode) DETACH DELETE n"
        run_query(cleanup_query)
        run_query(delete_temp_nodes)
        return Response({"error": str(e)}, status=500)