#!/usr/bin/env python3
"""
load_kg_to_neo4j.py

Load knowledge graph triples into Neo4j database.
Supports batch loading with progress tracking.

Usage:
    python load_kg_to_neo4j.py --kg kb.txt
    python load_kg_to_neo4j.py --kg kb.txt --batch-size 1000 --clear
"""

import argparse
import logging
import time
from typing import List, Tuple
import sys

try:
    from neo4j import GraphDatabase
except ImportError:
    print("ERROR: neo4j driver not installed!")
    print("Install with: pip install neo4j")
    sys.exit(1)


class Neo4jKGLoader:
    """Load KG triples into Neo4j."""
    
    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = "password123"
    ):
        """
        Initialize Neo4j connection.
        
        Args:
            uri: Neo4j URI
            user: Username
            password: Password
        """
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.logger = logging.getLogger(__name__)
    
    def close(self):
        """Close the driver connection."""
        self.driver.close()
    
    def clear_database(self):
        """Clear all nodes and relationships."""
        self.logger.warning("Clearing database...")
        
        with self.driver.session() as session:
            # Delete all relationships
            session.run("MATCH ()-[r]->() DELETE r")
            # Delete all nodes
            session.run("MATCH (n) DELETE n")
        
        self.logger.info("Database cleared")
    
    def create_indexes(self):
        """Create indexes for better query performance."""
        self.logger.info("Creating indexes...")
        
        with self.driver.session() as session:
            # Create index on Entity name
            session.run(
                "CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name)"
            )
            
            # Create index on Entity type
            session.run(
                "CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type)"
            )
        
        self.logger.info("Indexes created")
    
    def load_triples_batch(
        self,
        triples: List[Tuple[str, str, str]],
        batch_size: int = 1000
    ):
        """
        Load triples in batches using UNWIND.
        
        Args:
            triples: List of (subject, relation, object) tuples
            batch_size: Number of triples per batch
        """
        total_batches = (len(triples) + batch_size - 1) // batch_size
        
        with self.driver.session() as session:
            for i in range(0, len(triples), batch_size):
                batch = triples[i:i + batch_size]
                batch_num = i // batch_size + 1
                
                self.logger.info(
                    f"Loading batch {batch_num}/{total_batches} "
                    f"({len(batch)} triples)..."
                )
                
                # Convert to list of dicts for UNWIND
                batch_data = [
                    {"subject": s, "relation": r, "object": o}
                    for s, r, o in batch
                ]
                
                # Cypher query using UNWIND for batch insert
                query = """
                UNWIND $batch AS triple
                MERGE (s:Entity {name: triple.subject})
                MERGE (o:Entity {name: triple.object})
                MERGE (s)-[r:RELATION {type: triple.relation}]->(o)
                """
                
                session.run(query, batch=batch_data)
        
        self.logger.info(f"Loaded {len(triples)} triples")
    
    def load_triples_optimized(
        self,
        triples: List[Tuple[str, str, str]],
        batch_size: int = 5000
    ):
        """
        Optimized loading with typed relationships.
        Creates separate relationship types for each relation.
        
        Args:
            triples: List of (subject, relation, object) tuples
            batch_size: Number of triples per batch
        """
        from collections import defaultdict
        
        # Group triples by relation type
        grouped = defaultdict(list)
        for s, r, o in triples:
            grouped[r].append((s, o))
        
        self.logger.info(f"Found {len(grouped)} unique relation types")
        
        with self.driver.session() as session:
            for relation_type, pairs in grouped.items():
                self.logger.info(
                    f"Loading {len(pairs)} triples for relation: {relation_type}"
                )
                
                total_batches = (len(pairs) + batch_size - 1) // batch_size
                
                for i in range(0, len(pairs), batch_size):
                    batch = pairs[i:i + batch_size]
                    batch_num = i // batch_size + 1
                    
                    if total_batches > 1:
                        self.logger.info(
                            f"  Batch {batch_num}/{total_batches} "
                            f"({len(batch)} triples)"
                        )
                    
                    # Convert to list of dicts
                    batch_data = [
                        {"subject": s, "object": o}
                        for s, o in batch
                    ]
                    
                    # Create relationship with proper type
                    # Replace spaces and special chars in relation name
                    rel_name = relation_type.replace(' ', '_').replace('-', '_').upper()
                    
                    query = f"""
                    UNWIND $batch AS pair
                    MERGE (s:Entity {{name: pair.subject}})
                    MERGE (o:Entity {{name: pair.object}})
                    MERGE (s)-[r:{rel_name}]->(o)
                    """
                    
                    session.run(query, batch=batch_data)
        
        self.logger.info(f"Loaded {len(triples)} triples with typed relationships")
    
    def get_statistics(self):
        """Get database statistics."""
        with self.driver.session() as session:
            # Count nodes
            result = session.run("MATCH (n:Entity) RETURN count(n) as count")
            node_count = result.single()["count"]
            
            # Count relationships
            result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            rel_count = result.single()["count"]
            
            # Get unique relation types
            result = session.run("""
                MATCH ()-[r]->() 
                RETURN DISTINCT type(r) as rel_type, count(*) as count
                ORDER BY count DESC
            """)
            rel_types = [(record["rel_type"], record["count"]) for record in result]
        
        return {
            "nodes": node_count,
            "relationships": rel_count,
            "relation_types": rel_types
        }
    
    def test_connection(self):
        """Test Neo4j connection."""
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1 as test")
                result.single()
            return True
        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            return False


def load_kg_file(filepath: str, delimiter: str = '|') -> List[Tuple[str, str, str]]:
    """
    Load triples from a file.
    
    Args:
        filepath: Path to the KG file
        delimiter: Delimiter used in file
        
    Returns:
        List of (subject, relation, object) tuples
    """
    triples = []
    skipped = 0
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            parts = line.split(delimiter)
            if len(parts) != 3:
                skipped += 1
                logging.warning(f"Skipping malformed line {line_num}: {line}")
                continue
            
            subject, relation, obj = [p.strip() for p in parts]
            triples.append((subject, relation, obj))
    
    if skipped > 0:
        logging.warning(f"Skipped {skipped} malformed lines")
    
    return triples


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Load Knowledge Graph into Neo4j',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Load KG file
  %(prog)s --kg kb.txt
  
  # Clear database first
  %(prog)s --kg kb.txt --clear
  
  # Use custom connection
  %(prog)s --kg kb.txt --uri bolt://localhost:7687 --user neo4j --password mypass
  
  # Use optimized loading with typed relationships
  %(prog)s --kg kb.txt --optimized
  
  # Check statistics only
  %(prog)s --stats
        '''
    )
    
    parser.add_argument(
        '--kg',
        help='KG file to load (subject|relation|object format)'
    )
    parser.add_argument(
        '--delimiter',
        default='|',
        help='Delimiter in KG file (default: |)'
    )
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
    parser.add_argument(
        '--clear',
        action='store_true',
        help='Clear database before loading'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=5000,
        help='Batch size for loading (default: 5000)'
    )
    parser.add_argument(
        '--optimized',
        action='store_true',
        help='Use optimized loading with typed relationships'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show database statistics'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test connection only'
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(levelname)s: %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # Create loader
    try:
        loader = Neo4jKGLoader(
            uri=args.uri,
            user=args.user,
            password=args.password
        )
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {e}")
        logger.error("Make sure Neo4j is running with: docker-compose up -d")
        return 1
    
    try:
        # Test connection
        if args.test:
            if loader.test_connection():
                logger.info("✓ Connection successful!")
                return 0
            else:
                logger.error("✗ Connection failed!")
                return 1
        
        # Show statistics
        if args.stats:
            stats = loader.get_statistics()
            print("\n" + "=" * 60)
            print("NEO4J DATABASE STATISTICS")
            print("=" * 60)
            print(f"Nodes (Entities):    {stats['nodes']:,}")
            print(f"Relationships:       {stats['relationships']:,}")
            print(f"\nRelation Types:")
            for rel_type, count in stats['relation_types']:
                print(f"  {rel_type:30s} {count:>8,}")
            print("=" * 60)
            return 0
        
        # Load KG file
        if not args.kg:
            logger.error("--kg required (or use --stats/--test)")
            return 1
        
        # Load triples from file
        logger.info(f"Loading triples from {args.kg}...")
        start_time = time.time()
        triples = load_kg_file(args.kg, delimiter=args.delimiter)
        logger.info(f"Loaded {len(triples):,} triples from file")
        
        # Clear database if requested
        if args.clear:
            loader.clear_database()
        
        # Create indexes
        loader.create_indexes()
        
        # Load into Neo4j
        logger.info("Loading triples into Neo4j...")
        load_start = time.time()
        
        if args.optimized:
            loader.load_triples_optimized(triples, batch_size=args.batch_size)
        else:
            loader.load_triples_batch(triples, batch_size=args.batch_size)
        
        load_time = time.time() - load_start
        total_time = time.time() - start_time
        
        # Show statistics
        stats = loader.get_statistics()
        
        print("\n" + "=" * 60)
        print("LOADING COMPLETE")
        print("=" * 60)
        print(f"Total triples loaded: {len(triples):,}")
        print(f"Loading time:         {load_time:.2f}s")
        print(f"Total time:           {total_time:.2f}s")
        print(f"Throughput:           {len(triples)/load_time:.0f} triples/sec")
        print(f"\nDatabase Statistics:")
        print(f"  Nodes:              {stats['nodes']:,}")
        print(f"  Relationships:      {stats['relationships']:,}")
        print(f"  Relation types:     {len(stats['relation_types'])}")
        print("=" * 60)
        print(f"\nNeo4j Browser: http://localhost:7474")
        print(f"Username: {args.user}")
        print(f"Password: {args.password}")
        print("=" * 60)
        
        return 0
    
    except FileNotFoundError:
        logger.error(f"File not found: {args.kg}")
        return 1
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=args.verbose)
        return 1
    finally:
        loader.close()


if __name__ == "__main__":
    sys.exit(main())
