#!/usr/bin/env python3
"""
query_neo4j_paths.py

Query Neo4j for paths and generate questions.
Combines Neo4j path finding with question generation.

Usage:
    python query_neo4j_paths.py --find-paths --start "Kismet" --end "Josef von Sternberg"
    python query_neo4j_paths.py --n-hop --start "The Matrix" --length 2
"""

import argparse
import json
import logging
import sys
from typing import List, Dict, Any

try:
    from neo4j import GraphDatabase
except ImportError:
    print("ERROR: neo4j driver not installed!")
    print("Install with: pip install neo4j")
    sys.exit(1)


class Neo4jPathQuery:
    """Query paths from Neo4j."""
    
    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = "password123"
    ):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.logger = logging.getLogger(__name__)
    
    def close(self):
        self.driver.close()
    
    def find_paths(
        self,
        start: str,
        end: str,
        max_length: int = 3,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Find all paths between two entities.
        
        Args:
            start: Starting entity name
            end: Ending entity name
            max_length: Maximum path length
            limit: Maximum number of paths
            
        Returns:
            List of path dictionaries
        """
        query = f"""
        MATCH path = (start:Entity {{name: $start}})-[*1..{max_length}]->(end:Entity {{name: $end}})
        WITH path, length(path) as pathLength
        ORDER BY pathLength
        LIMIT $limit
        RETURN path, pathLength
        """
        
        paths = []
        with self.driver.session() as session:
            result = session.run(query, start=start, end=end, limit=limit)
            
            for record in result:
                path_obj = record["path"]
                path_data = self._extract_path_data(path_obj)
                paths.append(path_data)
        
        return paths
    
    def find_n_hop_paths(
        self,
        start: str,
        length: int,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Find all paths of exactly N hops from a starting entity.
        
        Args:
            start: Starting entity name
            length: Exact path length
            limit: Maximum number of paths
            
        Returns:
            List of path dictionaries
        """
        query = f"""
        MATCH path = (start:Entity {{name: $start}})-[*{length}]->()
        WITH path
        LIMIT $limit
        RETURN path
        """
        
        paths = []
        with self.driver.session() as session:
            result = session.run(query, start=start, limit=limit)
            
            for record in result:
                path_obj = record["path"]
                path_data = self._extract_path_data(path_obj)
                paths.append(path_data)
        
        return paths
    
    def find_pattern_paths(
        self,
        pattern: List[str],
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Find paths matching a relation pattern.
        
        Args:
            pattern: List of relation types
            limit: Maximum number of paths
            
        Returns:
            List of path dictionaries
        """
        # Build pattern string
        pattern_parts = []
        for i, rel in enumerate(pattern):
            rel_name = rel.replace(' ', '_').replace('-', '_').upper()
            pattern_parts.append(f"-[r{i}:{rel_name}]->")
        
        pattern_str = ''.join(pattern_parts) + "()"
        
        query = f"""
        MATCH path = (start:Entity){pattern_str}
        WITH path
        LIMIT $limit
        RETURN path
        """
        
        paths = []
        with self.driver.session() as session:
            result = session.run(query, limit=limit)
            
            for record in result:
                path_obj = record["path"]
                path_data = self._extract_path_data(path_obj)
                paths.append(path_data)
        
        return paths
    
    def get_entity_info(self, entity: str) -> Dict[str, Any]:
        """Get information about an entity."""
        query = """
        MATCH (e:Entity {name: $entity})
        OPTIONAL MATCH (e)-[r_out]->()
        OPTIONAL MATCH ()-[r_in]->(e)
        RETURN e, 
               collect(DISTINCT type(r_out)) as outgoing_relations,
               collect(DISTINCT type(r_in)) as incoming_relations,
               count(DISTINCT r_out) as outgoing_count,
               count(DISTINCT r_in) as incoming_count
        """
        
        with self.driver.session() as session:
            result = session.run(query, entity=entity)
            record = result.single()
            
            if not record:
                return {"error": f"Entity '{entity}' not found"}
            
            return {
                "entity": entity,
                "outgoing_relations": [r for r in record["outgoing_relations"] if r],
                "incoming_relations": [r for r in record["incoming_relations"] if r],
                "outgoing_count": record["outgoing_count"],
                "incoming_count": record["incoming_count"]
            }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self.driver.session() as session:
            # Count nodes
            result = session.run("MATCH (n:Entity) RETURN count(n) as count")
            node_count = result.single()["count"]
            
            # Count relationships
            result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            rel_count = result.single()["count"]
            
            # Get relation types
            result = session.run("""
                MATCH ()-[r]->() 
                RETURN DISTINCT type(r) as rel_type, count(*) as count
                ORDER BY count DESC
            """)
            rel_types = {record["rel_type"]: record["count"] for record in result}
        
        return {
            "nodes": node_count,
            "relationships": rel_count,
            "relation_types": rel_types
        }
    
    def _extract_path_data(self, path_obj) -> Dict[str, Any]:
        """Extract path data from Neo4j path object."""
        nodes = []
        relations = []
        
        # Extract nodes
        for node in path_obj.nodes:
            nodes.append(node["name"])
        
        # Extract relationships
        for rel in path_obj.relationships:
            relations.append(rel.type)
        
        # Build schema path
        schema_path = []
        for i in range(len(nodes)):
            schema_path.append(nodes[i])
            if i < len(relations):
                schema_path.append(relations[i])
        
        return {
            "nodes": nodes,
            "relations": relations,
            "schema_path": schema_path,
            "length": len(relations),
            "display": self._format_path(nodes, relations)
        }
    
    def _format_path(self, nodes: List[str], relations: List[str]) -> str:
        """Format path for display."""
        result = nodes[0]
        for i, rel in enumerate(relations):
            result += f" --[{rel}]--> {nodes[i + 1]}"
        return result


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Query Neo4j for KG paths',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Get database statistics
  %(prog)s --stats
  
  # Get entity information
  %(prog)s --entity-info "The Matrix"
  
  # Find paths between entities
  %(prog)s --find-paths --start "The Matrix" --end "Keanu Reeves"
  
  # Find all 2-hop paths
  %(prog)s --n-hop --start "The Matrix" --length 2 --limit 10
  
  # Find pattern matches
  %(prog)s --pattern "DIRECTED_BY,STARRED_ACTORS" --limit 10
  
  # Save results to file
  %(prog)s --n-hop --start "The Matrix" --length 2 --output paths.json
        '''
    )
    
    # Connection options
    parser.add_argument(
        '--uri',
        default='bolt://localhost:7687',
        help='Neo4j URI (default: bolt://localhost:7687)'
    )
    parser.add_argument(
        '--user',
        default='neo4j',
        help='Neo4j username (default: neo4j)'
    )
    parser.add_argument(
        '--password',
        default='password123',
        help='Neo4j password (default: password123)'
    )
    
    # Query type
    query_group = parser.add_mutually_exclusive_group()
    query_group.add_argument(
        '--stats',
        action='store_true',
        help='Show database statistics'
    )
    query_group.add_argument(
        '--entity-info',
        metavar='ENTITY',
        help='Get information about an entity'
    )
    query_group.add_argument(
        '--find-paths',
        action='store_true',
        help='Find paths between entities'
    )
    query_group.add_argument(
        '--n-hop',
        action='store_true',
        help='Find N-hop paths from entity'
    )
    query_group.add_argument(
        '--pattern',
        metavar='RELATIONS',
        help='Find paths matching pattern (comma-separated)'
    )
    
    # Query parameters
    parser.add_argument('--start', help='Starting entity')
    parser.add_argument('--end', help='Ending entity')
    parser.add_argument('--length', type=int, help='Path length for N-hop')
    parser.add_argument('--max-length', type=int, default=3, help='Max path length')
    parser.add_argument('--limit', type=int, default=100, help='Max results')
    
    # Output
    parser.add_argument('--output', help='Output JSON file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(levelname)s: %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # Create query client
    try:
        client = Neo4jPathQuery(
            uri=args.uri,
            user=args.user,
            password=args.password
        )
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {e}")
        logger.error("Make sure Neo4j is running with: docker-compose up -d")
        return 1
    
    try:
        results = None
        
        # Statistics
        if args.stats:
            stats = client.get_statistics()
            print("\n" + "=" * 60)
            print("NEO4J DATABASE STATISTICS")
            print("=" * 60)
            print(f"Nodes:          {stats['nodes']:,}")
            print(f"Relationships:  {stats['relationships']:,}")
            print(f"\nRelation Types:")
            for rel_type, count in sorted(stats['relation_types'].items(), 
                                         key=lambda x: x[1], reverse=True):
                print(f"  {rel_type:30s} {count:>8,}")
            print("=" * 60)
            return 0
        
        # Entity info
        elif args.entity_info:
            info = client.get_entity_info(args.entity_info)
            
            if "error" in info:
                logger.error(info["error"])
                return 1
            
            print(f"\nEntity: {info['entity']}")
            print(f"Outgoing: {info['outgoing_count']} relationships")
            print(f"Incoming: {info['incoming_count']} relationships")
            
            if info['outgoing_relations']:
                print("\nOutgoing Relations:")
                for rel in info['outgoing_relations']:
                    print(f"  - {rel}")
            
            if info['incoming_relations']:
                print("\nIncoming Relations:")
                for rel in info['incoming_relations']:
                    print(f"  - {rel}")
            
            return 0
        
        # Find paths
        elif args.find_paths:
            if not args.start or not args.end:
                logger.error("--find-paths requires --start and --end")
                return 1
            
            paths = client.find_paths(
                start=args.start,
                end=args.end,
                max_length=args.max_length,
                limit=args.limit
            )
            
            print(f"\nFound {len(paths)} path(s) from '{args.start}' to '{args.end}':\n")
            for i, path in enumerate(paths, 1):
                print(f"{i}. {path['display']}")
                print(f"   Length: {path['length']} hops")
                print()
            
            results = paths
        
        # N-hop
        elif args.n_hop:
            if not args.start or not args.length:
                logger.error("--n-hop requires --start and --length")
                return 1
            
            paths = client.find_n_hop_paths(
                start=args.start,
                length=args.length,
                limit=args.limit
            )
            
            print(f"\nFound {len(paths)} {args.length}-hop path(s) from '{args.start}':\n")
            for i, path in enumerate(paths, 1):
                print(f"{i}. {path['display']}")
                print()
            
            results = paths
        
        # Pattern
        elif args.pattern:
            pattern = [r.strip() for r in args.pattern.split(',')]
            
            paths = client.find_pattern_paths(
                pattern=pattern,
                limit=args.limit
            )
            
            print(f"\nFound {len(paths)} path(s) matching pattern {pattern}:\n")
            for i, path in enumerate(paths, 1):
                print(f"{i}. {path['display']}")
                print()
            
            results = paths
        
        else:
            parser.print_help()
            return 1
        
        # Save results
        if args.output and results:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"Results written to {args.output}")
        
        return 0
    
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=args.verbose)
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
