#!/usr/bin/env python3
"""
kg_type_mapper.py

Maps entity instances to their types using the KG schema.
Converts instance paths to typed schema paths for question generation.

Author: KG Type Mapper
Version: 1.0
"""

import argparse
import json
import logging
from pathlib import Path as FilePath
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict


class EntityTypeMapper:
    """
    Maps entity instances to their types based on KG structure.
    """
    
    def __init__(self):
        self.entity_types: Dict[str, str] = {}
        self.relation_types: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        self.logger = logging.getLogger(__name__)
    
    def load_from_kg(self, kg_file: str, delimiter: str = '|'):
        """
        Infer entity types from KG structure.
        Uses heuristics and relation patterns.
        """
        # Load triples
        triples = []
        with open(kg_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split(delimiter)
                if len(parts) == 3:
                    triples.append(tuple(p.strip() for p in parts))
        
        self.logger.info(f"Loaded {len(triples)} triples")
        
        # Build relation type map
        for subj, rel, obj in triples:
            # Infer types based on relations
            if rel == 'directed_by':
                # Movie directed by Person
                self.entity_types[obj] = 'person_name'
            elif rel == 'written_by':
                # Movie written by Person
                self.entity_types[obj] = 'person_name'
            elif rel == 'starred_actors':
                # Movie starred Person or Person starred in Movie
                # Need to check context
                pass
            elif rel == 'has_genre':
                # Movie has Genre
                self.entity_types[obj] = 'genre'
            elif rel == 'release_year':
                # Movie released in Year
                self.entity_types[obj] = 'year'
            elif rel == 'in_language':
                # Movie in Language
                self.entity_types[obj] = 'language'
            elif rel == 'has_tags':
                # Movie has Tag
                self.entity_types[obj] = 'tag'
        
        # Second pass: infer movie titles and actors
        for subj, rel, obj in triples:
            # If subject is used with movie-specific relations, it's a title
            if rel in ['directed_by', 'written_by', 'has_genre', 'release_year', 
                       'in_language', 'has_tags']:
                if subj not in self.entity_types:
                    self.entity_types[subj] = 'title'
            
            # For starred_actors, check if we know the types
            if rel == 'starred_actors':
                if subj in self.entity_types and self.entity_types[subj] == 'title':
                    # Title -> Person
                    self.entity_types[obj] = 'person_name'
                elif obj in self.entity_types and self.entity_types[obj] == 'title':
                    # Person -> Title
                    self.entity_types[subj] = 'person_name'
        
        self.logger.info(f"Mapped {len(self.entity_types)} entities to types")
    
    def load_from_schema(self, schema_file: str, delimiter: str = '|'):
        """
        Load type mappings from a schema file.
        Format: SUBJECT_TYPE|RELATIONSHIP|OBJECT_TYPE|FREQUENCY
        """
        with open(schema_file, 'r', encoding='utf-8') as f:
            # Skip header
            next(f)
            
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                parts = line.split(delimiter)
                if len(parts) == 4:
                    subj_type, rel, obj_type, freq = parts
                    self.relation_types[rel].append((subj_type, obj_type))
        
        self.logger.info(f"Loaded schema with {len(self.relation_types)} relations")
    
    def get_type(self, entity: str) -> Optional[str]:
        """Get the type of an entity."""
        return self.entity_types.get(entity)
    
    def infer_path_types(self, instance_path: List[str]) -> List[str]:
        """
        Convert instance path to typed schema path.
        
        Args:
            instance_path: [entity, relation, entity, relation, ...]
            
        Returns:
            Typed schema path with node types instead of instances
        """
        typed_path = []
        
        for i, element in enumerate(instance_path):
            if i % 2 == 0:  # Node
                entity_type = self.get_type(element)
                if entity_type:
                    typed_path.append(entity_type)
                else:
                    # Unknown type - try to infer from position
                    typed_path.append('unknown')
                    self.logger.warning(f"Unknown type for entity '{element}'")
            else:  # Relation
                typed_path.append(element)
        
        return typed_path
    
    def convert_paths(self, instance_paths: List[List[str]]) -> List[List[str]]:
        """Convert multiple instance paths to typed schema paths."""
        return [self.infer_path_types(path) for path in instance_paths]


def main():
    """CLI for type mapping."""
    parser = argparse.ArgumentParser(
        description='Map entity instances to types for schema paths',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Map from KG structure
  %(prog)s --kg kg.txt --paths instance_paths.json --output typed_paths.json
  
  # Map using schema file
  %(prog)s --kg kg.txt --schema kg_schema.txt --paths paths.json
        '''
    )
    
    parser.add_argument(
        '--kg',
        required=True,
        help='KG file for type inference'
    )
    parser.add_argument(
        '--schema',
        help='Optional schema file for better type inference'
    )
    parser.add_argument(
        '--paths',
        required=True,
        help='JSON file with instance paths'
    )
    parser.add_argument(
        '--output',
        help='Output file for typed paths'
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true'
    )
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(levelname)s: %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # Load mapper
    mapper = EntityTypeMapper()
    mapper.load_from_kg(args.kg)
    
    if args.schema:
        mapper.load_from_schema(args.schema)
    
    # Load instance paths
    with open(args.paths) as f:
        data = json.load(f)
    
    # Handle different input formats
    if isinstance(data, list):
        if data and isinstance(data[0], dict) and 'path' in data[0]:
            # Format: [{"path": [...], ...}, ...]
            instance_paths = [item['path'] for item in data]
        else:
            # Format: [[...], [...]]
            instance_paths = data
    else:
        logger.error("Invalid input format")
        return 1
    
    # Convert paths
    typed_paths = mapper.convert_paths(instance_paths)
    
    logger.info(f"Converted {len(typed_paths)} paths")
    
    # Output
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(typed_paths, f, indent=2)
        logger.info(f"Wrote typed paths to {args.output}")
    else:
        print(json.dumps(typed_paths, indent=2))
    
    return 0


if __name__ == "__main__":
    import sys