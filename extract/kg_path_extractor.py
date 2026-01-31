#!/usr/bin/env python3
"""
kg_path_extractor.py

Index and extract paths from Knowledge Graph triple files.
Supports multiple query types and efficient path finding.

Input format: subject|relation|object (one triple per line)
Example: Kismet|directed_by|William Dieterle

Author: KG Path Extractor
Version: 1.0
"""

import argparse
import json
import logging
from pathlib import Path as FilePath
from typing import List, Dict, Set, Tuple, Optional, Any
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
import sys


# ============================================================
# DATA STRUCTURES
# ============================================================

@dataclass
class Triple:
    """Represents a KG triple."""
    subject: str
    relation: str
    object: str
    
    def __str__(self):
        return f"{self.subject}|{self.relation}|{self.object}"
    
    def to_dict(self):
        return asdict(self)


@dataclass
class Path:
    """Represents a path in the KG."""
    nodes: List[str]
    relations: List[str]
    triples: List[Triple]
    
    def __len__(self):
        return len(self.relations)
    
    def __str__(self):
        result = self.nodes[0]
        for i, rel in enumerate(self.relations):
            result += f" --[{rel}]--> {self.nodes[i + 1]}"
        return result
    
    def to_schema_path(self) -> List[str]:
        """Convert to schema path format for question generator."""
        result = []
        for i in range(len(self.nodes)):
            result.append(self.nodes[i])
            if i < len(self.relations):
                result.append(self.relations[i])
        return result
    
    def to_dict(self):
        return {
            'nodes': self.nodes,
            'relations': self.relations,
            'path': self.to_schema_path(),
            'display': str(self),
            'length': len(self),
            'triples': [t.to_dict() for t in self.triples]
        }


# ============================================================
# KNOWLEDGE GRAPH INDEX
# ============================================================

class KnowledgeGraphIndex:
    """
    Efficient in-memory index for KG triples.
    Supports fast lookups and path finding.
    """
    
    def __init__(self):
        # Forward index: subject -> [(relation, object)]
        self.forward_index: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        
        # Backward index: object -> [(relation, subject)]
        self.backward_index: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        
        # Relation index: relation -> [(subject, object)]
        self.relation_index: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        
        # All triples
        self.triples: List[Triple] = []
        
        # Statistics
        self.stats = {
            'num_triples': 0,
            'num_entities': 0,
            'num_relations': 0,
            'num_subjects': 0,
            'num_objects': 0
        }
        
        self.logger = logging.getLogger(__name__)
    
    def load_from_file(self, filepath: FilePath, delimiter: str = '|'):
        """
        Load triples from a file.
        
        Args:
            filepath: Path to the triple file
            delimiter: Delimiter used in the file (default: |)
        """
        self.logger.info(f"Loading triples from {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split(delimiter)
                if len(parts) != 3:
                    self.logger.warning(
                        f"Skipping malformed line {line_num}: {line}"
                    )
                    continue
                
                subject, relation, obj = [p.strip() for p in parts]
                self.add_triple(subject, relation, obj)
        
        self._compute_stats()
        self.logger.info(f"Loaded {self.stats['num_triples']} triples")
    
    def add_triple(self, subject: str, relation: str, obj: str):
        """Add a single triple to the index."""
        triple = Triple(subject, relation, obj)
        self.triples.append(triple)
        
        # Update indices
        self.forward_index[subject].append((relation, obj))
        self.backward_index[obj].append((relation, subject))
        self.relation_index[relation].append((subject, obj))
    
    def _compute_stats(self):
        """Compute statistics about the KG."""
        all_entities = set()
        subjects = set()
        objects = set()
        relations = set()
        
        for triple in self.triples:
            all_entities.add(triple.subject)
            all_entities.add(triple.object)
            subjects.add(triple.subject)
            objects.add(triple.object)
            relations.add(triple.relation)
        
        self.stats = {
            'num_triples': len(self.triples),
            'num_entities': len(all_entities),
            'num_relations': len(relations),
            'num_subjects': len(subjects),
            'num_objects': len(objects)
        }
    
    def get_outgoing(self, entity: str) -> List[Tuple[str, str]]:
        """Get all outgoing edges from an entity."""
        return self.forward_index.get(entity, [])
    
    def get_incoming(self, entity: str) -> List[Tuple[str, str]]:
        """Get all incoming edges to an entity."""
        return self.backward_index.get(entity, [])
    
    def get_by_relation(self, relation: str) -> List[Tuple[str, str]]:
        """Get all (subject, object) pairs for a relation."""
        return self.relation_index.get(relation, [])
    
    def entity_exists(self, entity: str) -> bool:
        """Check if an entity exists in the KG."""
        return entity in self.forward_index or entity in self.backward_index
    
    def get_all_entities(self) -> Set[str]:
        """Get all unique entities."""
        entities = set()
        for triple in self.triples:
            entities.add(triple.subject)
            entities.add(triple.object)
        return entities
    
    def get_all_relations(self) -> Set[str]:
        """Get all unique relations."""
        return set(self.relation_index.keys())


# ============================================================
# PATH FINDER
# ============================================================

class PathFinder:
    """
    Find paths in the knowledge graph using BFS.
    """
    
    def __init__(self, kg_index: KnowledgeGraphIndex):
        self.kg = kg_index
        self.logger = logging.getLogger(__name__)
    
    def find_paths(
        self,
        start: str,
        end: str,
        max_length: int = 3,
        limit: Optional[int] = None
    ) -> List[Path]:
        """
        Find all paths from start to end entity.
        
        Args:
            start: Starting entity
            end: Ending entity
            max_length: Maximum path length (number of hops)
            limit: Maximum number of paths to return
            
        Returns:
            List of Path objects
        """
        if not self.kg.entity_exists(start):
            self.logger.warning(f"Start entity '{start}' not found in KG")
            return []
        
        if not self.kg.entity_exists(end):
            self.logger.warning(f"End entity '{end}' not found in KG")
            return []
        
        paths = []
        
        # BFS queue: (current_entity, path_nodes, path_relations, path_triples)
        queue = deque([(start, [start], [], [])])
        visited = set()
        
        while queue:
            if limit and len(paths) >= limit:
                break
            
            current, nodes, relations, triples = queue.popleft()
            
            # Create state key for cycle detection
            state = (current, len(nodes))
            if state in visited:
                continue
            visited.add(state)
            
            # Check if we reached the end
            if current == end and len(relations) > 0:
                path = Path(
                    nodes=nodes.copy(),
                    relations=relations.copy(),
                    triples=triples.copy()
                )
                paths.append(path)
                continue
            
            # Don't expand beyond max length
            if len(relations) >= max_length:
                continue
            
            # Expand to neighbors
            for relation, neighbor in self.kg.get_outgoing(current):
                # Avoid cycles (don't revisit nodes in current path)
                if neighbor not in nodes:
                    new_nodes = nodes + [neighbor]
                    new_relations = relations + [relation]
                    new_triples = triples + [
                        Triple(current, relation, neighbor)
                    ]
                    queue.append((neighbor, new_nodes, new_relations, new_triples))
        
        return paths
    
    def find_paths_by_pattern(
        self,
        pattern: List[str],
        limit: Optional[int] = None
    ) -> List[Path]:
        """
        Find paths matching a specific relation pattern.
        
        Args:
            pattern: List of relations to match (e.g., ["directed_by", "starred_actors"])
            limit: Maximum number of paths to return
            
        Returns:
            List of matching Path objects
        """
        if not pattern:
            return []
        
        paths = []
        
        # Start with all subjects that have the first relation
        first_relation = pattern[0]
        for subject, obj in self.kg.get_by_relation(first_relation):
            # Try to follow the pattern from this starting point
            matching_paths = self._follow_pattern(
                current=obj,
                remaining_pattern=pattern[1:],
                nodes=[subject, obj],
                relations=[first_relation],
                triples=[Triple(subject, first_relation, obj)]
            )
            paths.extend(matching_paths)
            
            if limit and len(paths) >= limit:
                break
        
        return paths[:limit] if limit else paths
    
    def _follow_pattern(
        self,
        current: str,
        remaining_pattern: List[str],
        nodes: List[str],
        relations: List[str],
        triples: List[Triple]
    ) -> List[Path]:
        """Recursively follow a relation pattern."""
        if not remaining_pattern:
            # Pattern complete
            return [Path(nodes=nodes, relations=relations, triples=triples)]
        
        next_relation = remaining_pattern[0]
        paths = []
        
        # Find all neighbors via this relation
        for relation, neighbor in self.kg.get_outgoing(current):
            if relation == next_relation and neighbor not in nodes:
                new_paths = self._follow_pattern(
                    current=neighbor,
                    remaining_pattern=remaining_pattern[1:],
                    nodes=nodes + [neighbor],
                    relations=relations + [relation],
                    triples=triples + [Triple(current, relation, neighbor)]
                )
                paths.extend(new_paths)
        
        return paths
    
    def find_all_paths_from(
        self,
        start: str,
        length: int,
        limit: Optional[int] = None
    ) -> List[Path]:
        """
        Find all paths of a specific length starting from an entity.
        
        Args:
            start: Starting entity
            length: Exact path length (number of hops)
            limit: Maximum number of paths to return
            
        Returns:
            List of Path objects
        """
        if not self.kg.entity_exists(start):
            self.logger.warning(f"Start entity '{start}' not found in KG")
            return []
        
        paths = []
        queue = deque([(start, [start], [], [])])
        
        while queue:
            if limit and len(paths) >= limit:
                break
            
            current, nodes, relations, triples = queue.popleft()
            
            # If we've reached the desired length, save the path
            if len(relations) == length:
                path = Path(
                    nodes=nodes.copy(),
                    relations=relations.copy(),
                    triples=triples.copy()
                )
                paths.append(path)
                continue
            
            # Expand to neighbors
            for relation, neighbor in self.kg.get_outgoing(current):
                if neighbor not in nodes:  # Avoid cycles
                    new_nodes = nodes + [neighbor]
                    new_relations = relations + [relation]
                    new_triples = triples + [Triple(current, relation, neighbor)]
                    queue.append((neighbor, new_nodes, new_relations, new_triples))
        
        return paths


# ============================================================
# QUERY INTERFACE
# ============================================================

class KGQueryEngine:
    """High-level query interface for the KG."""
    
    def __init__(self, kg_index: KnowledgeGraphIndex):
        self.kg = kg_index
        self.path_finder = PathFinder(kg_index)
        self.logger = logging.getLogger(__name__)
    
    def query(self, query_type: str, **kwargs) -> List[Any]:
        """
        Execute a query on the KG.
        
        Supported query types:
        - 'entity_info': Get all triples involving an entity
        - 'find_paths': Find paths between two entities
        - 'pattern_match': Find paths matching a relation pattern
        - 'n_hop': Find all N-hop paths from an entity
        - 'relation_stats': Get statistics about a relation
        """
        if query_type == 'entity_info':
            return self._query_entity_info(kwargs.get('entity'))
        
        elif query_type == 'find_paths':
            return self.path_finder.find_paths(
                start=kwargs.get('start'),
                end=kwargs.get('end'),
                max_length=kwargs.get('max_length', 3),
                limit=kwargs.get('limit')
            )
        
        elif query_type == 'pattern_match':
            return self.path_finder.find_paths_by_pattern(
                pattern=kwargs.get('pattern'),
                limit=kwargs.get('limit')
            )
        
        elif query_type == 'n_hop':
            return self.path_finder.find_all_paths_from(
                start=kwargs.get('start'),
                length=kwargs.get('length'),
                limit=kwargs.get('limit')
            )
        
        elif query_type == 'relation_stats':
            return self._query_relation_stats(kwargs.get('relation'))
        
        else:
            raise ValueError(f"Unknown query type: {query_type}")
    
    def _query_entity_info(self, entity: str) -> Dict:
        """Get comprehensive information about an entity."""
        if not self.kg.entity_exists(entity):
            return {'error': f"Entity '{entity}' not found"}
        
        outgoing = self.kg.get_outgoing(entity)
        incoming = self.kg.get_incoming(entity)
        
        return {
            'entity': entity,
            'outgoing_count': len(outgoing),
            'incoming_count': len(incoming),
            'outgoing': [{'relation': r, 'object': o} for r, o in outgoing],
            'incoming': [{'relation': r, 'subject': s} for r, s in incoming]
        }
    
    def _query_relation_stats(self, relation: str) -> Dict:
        """Get statistics about a relation."""
        pairs = self.kg.get_by_relation(relation)
        
        if not pairs:
            return {'error': f"Relation '{relation}' not found"}
        
        subjects = set(s for s, _ in pairs)
        objects = set(o for _, o in pairs)
        
        return {
            'relation': relation,
            'count': len(pairs),
            'unique_subjects': len(subjects),
            'unique_objects': len(objects),
            'sample_triples': [
                {'subject': s, 'object': o} for s, o in pairs[:10]
            ]
        }


# ============================================================
# CLI INTERFACE
# ============================================================

def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(levelname)s: %(message)s'
    )


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Index and extract paths from Knowledge Graph files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Load KG and show statistics
  %(prog)s --load kg.txt --stats
  
  # Find paths between entities
  %(prog)s --load kg.txt --find-paths --start "Kismet" --end "Marlene Dietrich"
  
  # Find all 2-hop paths from an entity
  %(prog)s --load kg.txt --n-hop --start "Kismet" --length 2
  
  # Find paths matching a pattern
  %(prog)s --load kg.txt --pattern "directed_by,starred_actors"
  
  # Get entity information
  %(prog)s --load kg.txt --entity-info "Kismet"
  
  # Export paths to JSON
  %(prog)s --load kg.txt --find-paths --start "Kismet" --end "Edward Arnold" --output paths.json
        '''
    )
    
    # Input options
    parser.add_argument(
        '--load',
        type=str,
        required=True,
        help='KG file to load (format: subject|relation|object)'
    )
    parser.add_argument(
        '--delimiter',
        type=str,
        default='|',
        help='Delimiter used in KG file (default: |)'
    )
    
    # Query options
    query_group = parser.add_mutually_exclusive_group()
    query_group.add_argument(
        '--stats',
        action='store_true',
        help='Show KG statistics'
    )
    query_group.add_argument(
        '--entity-info',
        type=str,
        metavar='ENTITY',
        help='Get information about an entity'
    )
    query_group.add_argument(
        '--find-paths',
        action='store_true',
        help='Find paths between two entities (requires --start and --end)'
    )
    query_group.add_argument(
        '--pattern',
        type=str,
        metavar='RELATIONS',
        help='Find paths matching relation pattern (comma-separated)'
    )
    query_group.add_argument(
        '--n-hop',
        action='store_true',
        help='Find all N-hop paths from entity (requires --start and --length)'
    )
    
    # Query parameters
    parser.add_argument(
        '--start',
        type=str,
        help='Starting entity for path queries'
    )
    parser.add_argument(
        '--end',
        type=str,
        help='Ending entity for path queries'
    )
    parser.add_argument(
        '--length',
        type=int,
        help='Path length for N-hop queries'
    )
    parser.add_argument(
        '--max-length',
        type=int,
        default=3,
        help='Maximum path length (default: 3)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Maximum number of results to return'
    )
    
    # Output options
    parser.add_argument(
        '--output',
        type=str,
        help='Output file for results (JSON format)'
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # Convert paths
    load_path = FilePath(args.load)
    output_path = FilePath(args.output) if args.output else None
    
    # Load KG
    if not load_path.exists():
        logger.error(f"File not found: {load_path}")
        return 1
    
    kg = KnowledgeGraphIndex()
    kg.load_from_file(load_path, delimiter=args.delimiter)
    
    # Execute query
    results = None
    
    if args.stats:
        # Show statistics
        print("\n" + "=" * 60)
        print("KNOWLEDGE GRAPH STATISTICS")
        print("=" * 60)
        print(f"Total triples:      {kg.stats['num_triples']:,}")
        print(f"Unique entities:    {kg.stats['num_entities']:,}")
        print(f"Unique relations:   {kg.stats['num_relations']:,}")
        print(f"Unique subjects:    {kg.stats['num_subjects']:,}")
        print(f"Unique objects:     {kg.stats['num_objects']:,}")
        print("\nRelations:")
        for rel in sorted(kg.get_all_relations()):
            count = len(kg.get_by_relation(rel))
            print(f"  {rel:30s} {count:>6,} triples")
        print("=" * 60)
        return 0
    
    # Create query engine
    query_engine = KGQueryEngine(kg)
    
    if args.entity_info:
        results = query_engine.query('entity_info', entity=args.entity_info)
        
        if 'error' in results:
            logger.error(results['error'])
            return 1
        
        print(f"\nEntity: {results['entity']}")
        print(f"Outgoing edges: {results['outgoing_count']}")
        print(f"Incoming edges: {results['incoming_count']}")
        
        if results['outgoing']:
            print("\nOutgoing:")
            for edge in results['outgoing']:
                print(f"  --[{edge['relation']}]--> {edge['object']}")
        
        if results['incoming']:
            print("\nIncoming:")
            for edge in results['incoming']:
                print(f"  <--[{edge['relation']}]-- {edge['subject']}")
    
    elif args.find_paths:
        if not args.start or not args.end:
            logger.error("--find-paths requires --start and --end")
            return 1
        
        paths = query_engine.query(
            'find_paths',
            start=args.start,
            end=args.end,
            max_length=args.max_length,
            limit=args.limit
        )
        
        print(f"\nFound {len(paths)} path(s) from '{args.start}' to '{args.end}':")
        for i, path in enumerate(paths, 1):
            print(f"\n{i}. {path}")
            print(f"   Schema path: {path.to_schema_path()}")
        
        results = [p.to_dict() for p in paths]
    
    elif args.pattern:
        pattern = [r.strip() for r in args.pattern.split(',')]
        
        paths = query_engine.query(
            'pattern_match',
            pattern=pattern,
            limit=args.limit
        )
        
        print(f"\nFound {len(paths)} path(s) matching pattern {pattern}:")
        for i, path in enumerate(paths, 1):
            print(f"\n{i}. {path}")
            print(f"   Schema path: {path.to_schema_path()}")
        
        results = [p.to_dict() for p in paths]
    
    elif args.n_hop:
        if not args.start or not args.length:
            logger.error("--n-hop requires --start and --length")
            return 1
        
        paths = query_engine.query(
            'n_hop',
            start=args.start,
            length=args.length,
            limit=args.limit
        )
        
        print(f"\nFound {len(paths)} {args.length}-hop path(s) from '{args.start}':")
        for i, path in enumerate(paths, 1):
            print(f"\n{i}. {path}")
            print(f"   Schema path: {path.to_schema_path()}")
        
        results = [p.to_dict() for p in paths]
    
    # Save results if requested
    if output_path and results:
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results written to {output_path}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())