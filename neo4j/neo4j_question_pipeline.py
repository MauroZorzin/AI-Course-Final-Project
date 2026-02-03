#!/usr/bin/env python3
"""
neo4j_question_pipeline.py

Complete pipeline: Extract paths from Neo4j → Generate questions
Supports random sampling and golden path specification.

Usage:
    # Random 2-hop paths
    python neo4j_question_pipeline.py --random --length 2 --count 100
    
    # Paths from specific entity
    python neo4j_question_pipeline.py --start "The Matrix" --length 2 --count 50
    
    # Specific golden path
    python neo4j_question_pipeline.py --golden-path "The Matrix" "Keanu Reeves"
    
    # Random with pattern
    python neo4j_question_pipeline.py --random --pattern "DIRECTED_BY,STARRED_ACTORS" --count 50
"""

import argparse
import json
import logging
import random
import sys
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

try:
    from neo4j import GraphDatabase
except ImportError:
    print("ERROR: neo4j driver not installed!")
    print("Install with: pip install neo4j")
    sys.exit(1)


# ============================================================
# TYPE INFERENCE
# ============================================================

class EntityTypeInferencer:
    """Infer entity types from Neo4j relationships."""
    
    def __init__(self, driver):
        self.driver = driver
        self.entity_cache = {}
        self.logger = logging.getLogger(__name__)
    
    def infer_type(self, entity: str, context_relations: List[str] = None) -> str:
        """
        Infer the type of an entity based on its relationships.
        
        Args:
            entity: Entity name
            context_relations: Relationships this entity participates in (for context)
            
        Returns:
            Entity type (title, person_name, genre, year, etc.)
        """
        # Check cache first
        if entity in self.entity_cache:
            return self.entity_cache[entity]
        
        # Try to infer from entity name/value patterns
        # Check if it's a year (4-digit number)
        if entity.isdigit() and len(entity) == 4:
            entity_type = 'year'
            self.entity_cache[entity] = entity_type
            return entity_type
        
        # Check if it's a number
        if entity.replace('.', '').replace('-', '').isdigit():
            entity_type = 'number'
            self.entity_cache[entity] = entity_type
            return entity_type
        
        # Query Neo4j for relationships
        with self.driver.session() as session:
            # Get all relationships (outgoing and incoming)
            result = session.run("""
                MATCH (e:Entity {name: $entity})
                OPTIONAL MATCH (e)-[r_out]->()
                OPTIONAL MATCH ()-[r_in]->(e)
                RETURN 
                    collect(DISTINCT type(r_out)) as outgoing_rels,
                    collect(DISTINCT type(r_in)) as incoming_rels
            """, entity=entity)
            
            record = result.single()
            if not record:
                # Entity not found, use heuristic
                return 'unknown'
            
            outgoing_rels = [r for r in record["outgoing_rels"] if r]
            incoming_rels = [r for r in record["incoming_rels"] if r]
        
        # Infer type based on relationships
        entity_type = self._infer_from_relationships(outgoing_rels, incoming_rels, entity)
        
        self.entity_cache[entity] = entity_type
        return entity_type
    
    def _infer_from_relationships(self, outgoing_rels: List[str], incoming_rels: List[str], entity: str) -> str:
        """Infer entity type from its relationships."""
        
        # Movie/Title indicators - entities that have these OUTGOING relations are movies
        movie_indicators = {
            'DIRECTED_BY', 'WRITTEN_BY', 'HAS_GENRE', 'RELEASE_YEAR',
            'IN_LANGUAGE', 'HAS_TAGS', 'HAS_IMDB_RATING', 'HAS_IMDB_VOTES'
        }
        
        # Person indicators - entities that have these OUTGOING relations are people
        person_indicators = {
            'ACTED_IN', 'DIRECTED', 'WROTE'
        }
        
        # Check if entity is a movie (has movie-specific outgoing relations)
        if any(rel in movie_indicators for rel in outgoing_rels):
            return 'title'
        
        # Check if entity receives movie relations (is target of movie relations)
        # These are typically people, genres, years, etc.
        
        # If target of DIRECTED_BY, WRITTEN_BY -> person
        if 'DIRECTED_BY' in incoming_rels or 'WRITTEN_BY' in incoming_rels:
            return 'person_name'
        
        # If target of HAS_GENRE -> genre
        if 'HAS_GENRE' in incoming_rels:
            return 'genre'
        
        # If target of RELEASE_YEAR -> year
        if 'RELEASE_YEAR' in incoming_rels:
            return 'year'
        
        # If target of IN_LANGUAGE -> language
        if 'IN_LANGUAGE' in incoming_rels:
            return 'language'
        
        # If target of HAS_TAGS or HAS_IMDB_RATING -> tag
        if 'HAS_TAGS' in incoming_rels or 'HAS_IMDB_RATING' in incoming_rels:
            return 'tag'
        
        # STARRED_ACTORS is bidirectional - need more context
        # If has STARRED_ACTORS outgoing but no movie indicators, likely a person
        if 'STARRED_ACTORS' in outgoing_rels and not any(rel in movie_indicators for rel in outgoing_rels):
            return 'person_name'
        
        # If receives STARRED_ACTORS and no movie indicators, likely a person
        if 'STARRED_ACTORS' in incoming_rels and not any(rel in movie_indicators for rel in outgoing_rels):
            return 'person_name'
        
        # Default: check if looks like a person name (has capital letters and spaces/multiple words)
        if ' ' in entity or (entity and entity[0].isupper()):
            return 'person_name'
        
        # Fallback
        return 'unknown'
    
    def infer_path_types(self, nodes: List[str], relations: List[str]) -> List[str]:
        """
        Convert instance path to typed schema path.
        
        Args:
            nodes: List of entity names
            relations: List of relation types
            
        Returns:
            Typed schema path [type, relation, type, relation, ...]
        """
        typed_path = []
        
        for i, node in enumerate(nodes):
            # Get context from adjacent relations
            context_rels = []
            if i > 0:
                context_rels.append(relations[i-1])
            if i < len(relations):
                context_rels.append(relations[i])
            
            # Infer node type with context
            node_type = self.infer_type(node, context_rels)
            typed_path.append(node_type)
            
            # Add relation (convert to lowercase with underscores)
            if i < len(relations):
                rel = relations[i].lower()
                typed_path.append(rel)
        
        return typed_path


# ============================================================
# NEO4J PATH EXTRACTOR
# ============================================================

class Neo4jPathExtractor:
    """Extract paths from Neo4j with various strategies."""
    
    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = "password123"
    ):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.type_inferencer = EntityTypeInferencer(self.driver)
        self.logger = logging.getLogger(__name__)
    
    def close(self):
        self.driver.close()
    
    def extract_random_paths(
        self,
        length: int,
        count: int,
        pattern: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract random paths of specified length.
        
        Args:
            length: Path length (number of hops)
            count: Number of paths to extract
            pattern: Optional relation pattern to match
            
        Returns:
            List of path dictionaries
        """
        self.logger.info(f"Extracting {count} random {length}-hop paths...")
        
        if pattern:
            return self._extract_random_pattern_paths(pattern, count)
        
        # Get random starting entities
        with self.driver.session() as session:
            result = session.run("""
                MATCH (n:Entity)
                WITH n, rand() as r
                ORDER BY r
                LIMIT $count
                RETURN n.name as entity
            """, count=count * 2)  # Get extra in case some don't have paths
            
            start_entities = [record["entity"] for record in result]
        
        # Extract paths from each starting entity
        all_paths = []
        for entity in start_entities:
            if len(all_paths) >= count:
                break
            
            paths = self._extract_n_hop_paths(entity, length, limit=1)
            all_paths.extend(paths)
        
        # Randomly sample if we have too many
        if len(all_paths) > count:
            all_paths = random.sample(all_paths, count)
        
        self.logger.info(f"Extracted {len(all_paths)} paths")
        return all_paths
    
    def extract_paths_from_entity(
        self,
        start: str,
        length: int,
        count: int
    ) -> List[Dict[str, Any]]:
        """
        Extract paths starting from a specific entity.
        
        Args:
            start: Starting entity
            length: Path length
            count: Maximum number of paths
            
        Returns:
            List of path dictionaries
        """
        self.logger.info(f"Extracting {length}-hop paths from '{start}'...")
        paths = self._extract_n_hop_paths(start, length, limit=count)
        self.logger.info(f"Extracted {len(paths)} paths")
        return paths
    
    def extract_golden_path(
        self,
        start: str,
        end: str,
        max_length: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Extract the golden path(s) between two entities.
        
        Args:
            start: Starting entity
            end: Ending entity
            max_length: Maximum path length to search
            
        Returns:
            List of path dictionaries
        """
        self.logger.info(f"Finding golden path from '{start}' to '{end}'...")
        
        query = f"""
        MATCH path = (start:Entity {{name: $start}})-[*1..{max_length}]->(end:Entity {{name: $end}})
        WITH path, length(path) as pathLength
        ORDER BY pathLength
        LIMIT 10
        RETURN path
        """
        
        paths = []
        with self.driver.session() as session:
            result = session.run(query, start=start, end=end)
            
            for record in result:
                path_obj = record["path"]
                path_data = self._extract_path_data(path_obj)
                paths.append(path_data)
        
        self.logger.info(f"Found {len(paths)} golden path(s)")
        return paths
    
    def extract_pattern_paths(
        self,
        pattern: List[str],
        count: int
    ) -> List[Dict[str, Any]]:
        """
        Extract paths matching a specific relation pattern.
        
        Args:
            pattern: List of relation types
            count: Maximum number of paths
            
        Returns:
            List of path dictionaries
        """
        self.logger.info(f"Extracting paths matching pattern {pattern}...")
        
        # Build pattern string
        pattern_parts = []
        for i, rel in enumerate(pattern):
            pattern_parts.append(f"-[r{i}:{rel}]->")
        pattern_str = ''.join(pattern_parts) + "()"
        
        query = f"""
        MATCH path = (start:Entity){pattern_str}
        WITH path, rand() as r
        ORDER BY r
        LIMIT $count
        RETURN path
        """
        
        paths = []
        with self.driver.session() as session:
            result = session.run(query, count=count)
            
            for record in result:
                path_obj = record["path"]
                path_data = self._extract_path_data(path_obj)
                paths.append(path_data)
        
        self.logger.info(f"Extracted {len(paths)} paths")
        return paths
    
    def _extract_n_hop_paths(
        self,
        start: str,
        length: int,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Extract N-hop paths from a starting entity."""
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
    
    def _extract_random_pattern_paths(
        self,
        pattern: List[str],
        count: int
    ) -> List[Dict[str, Any]]:
        """Extract random paths matching a pattern."""
        return self.extract_pattern_paths(pattern, count)
    
    def _extract_path_data(self, path_obj) -> Dict[str, Any]:
        """Extract and type a path from Neo4j path object."""
        nodes = []
        relations = []
        
        # Extract nodes and relations
        for node in path_obj.nodes:
            nodes.append(node["name"])
        
        for rel in path_obj.relationships:
            # Get actual relationship type, not generic "RELATION"
            rel_type = rel.type
            relations.append(rel_type)
        
        # Infer types for schema path
        typed_path = self.type_inferencer.infer_path_types(nodes, relations)
        
        return {
            "instance_nodes": nodes,
            "relations": relations,
            "typed_path": typed_path,
            "length": len(relations),
            "display": self._format_path(nodes, relations)
        }
    
    def _format_path(self, nodes: List[str], relations: List[str]) -> str:
        """Format path for display."""
        result = nodes[0]
        for i, rel in enumerate(relations):
            result += f" --[{rel}]--> {nodes[i + 1]}"
        return result


# ============================================================
# QUESTION GENERATOR (Simplified)
# ============================================================

class QuestionGenerator:
    """Generate questions from typed schema paths that match the actual path structure."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def generate_question(self, typed_path: List[str], instance_path: List[str]) -> str:
        """
        Generate a question that asks about the END of the path, given the START.
        
        Examples:
        Path: The Matrix -> STARRED_ACTORS -> Keanu Reeves -> STARRED_ACTORS -> John Wick
        Question: "Which movies starred actors from The Matrix?"
        
        Path: Inception -> DIRECTED_BY -> Nolan -> DIRECTED_BY -> Interstellar
        Question: "Which movies were directed by the director of Inception?"
        
        Args:
            typed_path: [type, relation, type, relation, ...]
            instance_path: [entity1, entity2, entity3, ...]
            
        Returns:
            Natural language question
        """
        if len(typed_path) < 3 or len(typed_path) % 2 == 0:
            raise ValueError("Invalid path format")
        
        start_entity = instance_path[0]
        end_type = typed_path[-1]
        
        # Determine what we're asking for (WH-word)
        wh_word = self._get_wh_word(end_type)
        
        # Build the description of how to traverse the path
        path_description = self._describe_path(typed_path, instance_path)
        
        # Combine into question
        question = f"{wh_word} {path_description}?"
        
        return question
    
    def _get_wh_word(self, entity_type: str) -> str:
        """Get the appropriate WH-word for the target entity type."""
        wh_words = {
            "person_name": "Who",
            "title": "Which movies",
            "genre": "Which genres",
            "year": "Which years",
            "language": "Which languages",
            "tag": "Which tags",
            "number": "What numbers",
            "unknown": "What"
        }
        return wh_words.get(entity_type, "What")
    
    def _describe_path(self, typed_path: List[str], instance_path: List[str]) -> str:
        """
        Describe the path from start to end.
        
        Strategy: Work backwards from the target, building up the description.
        """
        # Single hop - special case (simpler phrasing)
        if len(typed_path) == 3:
            return self._describe_single_hop(
                instance_path[0],
                typed_path[0],
                typed_path[1],
                typed_path[2]
            )
        
        # Multi-hop - build backwards from target
        # The pattern is: "verb the {intermediate_description} of {start_entity}"
        
        start_entity = instance_path[0]
        description_parts = []
        
        # Start from the last relation and work backwards
        for i in range(len(typed_path) - 2, 0, -2):
            relation = typed_path[i]
            source_type = typed_path[i - 1]
            target_type = typed_path[i + 1]
            
            # Index in instance_path (every 2 elements in typed_path = 1 in instance_path)
            source_idx = (i - 1) // 2
            
            if i == len(typed_path) - 2:
                # This is the final hop to the target
                verb_phrase = self._get_final_hop_verb(relation, source_type, target_type)
                description_parts.append(verb_phrase)
            else:
                # This is an intermediate hop
                intermediate_entity = instance_path[source_idx + 1]
                intermediate_desc = self._get_intermediate_desc(relation, source_type, intermediate_entity)
                description_parts.append(intermediate_desc)
        
        # Add the starting entity reference
        description_parts.append(start_entity)
        
        # Join the parts
        result = " ".join(description_parts)
        
        return result
    
    def _describe_single_hop(self, start_entity: str, start_type: str, relation: str, end_type: str) -> str:
        """Describe a single-hop path."""
        
        # Movie -> Person
        if start_type == "title" and end_type == "person_name":
            if relation == "directed_by":
                return f"directed {start_entity}"
            elif relation == "written_by":
                return f"wrote {start_entity}"
            elif relation == "starred_actors":
                return f"starred in {start_entity}"
        
        # Movie -> Genre
        elif start_type == "title" and end_type == "genre":
            return f"is the genre of {start_entity}"
        
        # Movie -> Year
        elif start_type == "title" and end_type == "year":
            return f"is the release year of {start_entity}"
        
        # Person -> Movie  
        elif start_type == "person_name" and end_type == "title":
            if relation == "directed_by":
                return f"did {start_entity} direct"
            elif relation == "starred_actors":
                return f"did {start_entity} star in"
        
        # Fallback
        return f"{relation.replace('_', ' ')} {start_entity}"
    
    def _get_final_hop_verb(self, relation: str, source_type: str, target_type: str) -> str:
        """Get the verb phrase for the final hop to the target."""
        
        # Movie as target
        if target_type == "title":
            if relation == "directed_by":
                return "were directed by the director of"
            elif relation == "written_by":
                return "were written by the writer of"
            elif relation == "starred_actors":
                return "starred actors from"
            elif relation == "has_genre":
                return "are in the same genre as"
        
        # Person as target
        elif target_type == "person_name":
            if relation == "directed_by":
                return "directed"
            elif relation == "written_by":
                return "wrote"
            elif relation == "starred_actors":
                return "starred in"
        
        # Genre as target
        elif target_type == "genre":
            if relation == "has_genre":
                return "is the genre of"
        
        # Year as target
        elif target_type == "year":
            if relation == "release_year":
                return "was the release year of"
        
        # Fallback
        return relation.replace("_", " ")
    
    def _get_intermediate_desc(self, relation: str, entity_type: str, entity: str) -> str:
        """Get description for an intermediate entity in the path."""
        
        if relation == "directed_by":
            return f"the director of {entity},"
        elif relation == "written_by":
            return f"the writer of {entity},"
        elif relation == "starred_actors":
            return f"actors who starred in {entity},"
        elif relation == "has_genre":
            return f"movies in the same genre as {entity},"
        else:
            return f"{relation.replace('_', ' ')} {entity},"


# ============================================================
# COMPLETE PIPELINE
# ============================================================

class QuestionPipeline:
    """Complete pipeline from Neo4j to questions."""
    
    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = "password123"
    ):
        self.extractor = Neo4jPathExtractor(uri, user, password)
        self.generator = QuestionGenerator()
        self.logger = logging.getLogger(__name__)
    
    def close(self):
        self.extractor.close()
    
    def run_random(
        self,
        length: int,
        count: int,
        pattern: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate questions from random paths.
        
        Args:
            length: Path length
            count: Number of questions
            pattern: Optional relation pattern
            
        Returns:
            List of results with paths and questions
        """
        # Extract paths
        paths = self.extractor.extract_random_paths(length, count, pattern)
        
        # Generate questions
        results = []
        for path in paths:
            result = self._process_path(path)
            results.append(result)
        
        return results
    
    def run_from_entity(
        self,
        start: str,
        length: int,
        count: int
    ) -> List[Dict[str, Any]]:
        """
        Generate questions from paths starting at a specific entity.
        
        Args:
            start: Starting entity
            length: Path length
            count: Number of questions
            
        Returns:
            List of results
        """
        # Extract paths
        paths = self.extractor.extract_paths_from_entity(start, length, count)
        
        # Generate questions
        results = []
        for path in paths:
            result = self._process_path(path)
            results.append(result)
        
        return results
    
    def run_golden_path(
        self,
        start: str,
        end: str,
        max_length: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Generate questions from golden paths between entities.
        
        Args:
            start: Starting entity
            end: Ending entity
            max_length: Maximum path length
            
        Returns:
            List of results
        """
        # Extract golden paths
        paths = self.extractor.extract_golden_path(start, end, max_length)
        
        # Generate questions
        results = []
        for path in paths:
            result = self._process_path(path)
            results.append(result)
        
        return results
    
    def run_pattern(
        self,
        pattern: List[str],
        count: int
    ) -> List[Dict[str, Any]]:
        """
        Generate questions from pattern-matched paths.
        
        Args:
            pattern: Relation pattern
            count: Number of questions
            
        Returns:
            List of results
        """
        # Extract paths
        paths = self.extractor.extract_pattern_paths(pattern, count)
        
        # Generate questions
        results = []
        for path in paths:
            result = self._process_path(path)
            results.append(result)
        
        return results
    
    def _process_path(self, path: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single path to generate question."""
        try:
            question = self.generator.generate_question(
                path["typed_path"], 
                path["instance_nodes"]
            )
            
            return {
                "success": True,
                "instance_path": path["instance_nodes"],
                "relations": path["relations"],
                "typed_path": path["typed_path"],
                "question": question,
                "display": path["display"],
                "length": path["length"]
            }
        except Exception as e:
            self.logger.warning(f"Failed to generate question: {e}")
            return {
                "success": False,
                "instance_path": path["instance_nodes"],
                "relations": path["relations"],
                "typed_path": path["typed_path"],
                "error": str(e),
                "display": path["display"],
                "length": path["length"]
            }


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description='Neo4j Path Extraction & Question Generation Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Random 2-hop paths
  %(prog)s --random --length 2 --count 100
  
  # Random 3-hop paths with pattern
  %(prog)s --random --length 3 --count 50 --pattern "DIRECTED_BY,STARRED_ACTORS"
  
  # Paths from specific entity
  %(prog)s --start "The Matrix" --length 2 --count 50
  
  # Golden path between entities
  %(prog)s --golden-path "The Matrix" "Keanu Reeves"
  
  # Pattern-based extraction
  %(prog)s --pattern "DIRECTED_BY,STARRED_ACTORS" --count 100
  
  # Save to file
  %(prog)s --random --length 2 --count 100 --output questions.json
        '''
    )
    
    # Connection
    parser.add_argument('--uri', default='bolt://localhost:7687')
    parser.add_argument('--user', default='neo4j')
    parser.add_argument('--password', default='password123')
    
    # Mode selection
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--random', action='store_true', 
                           help='Extract random paths')
    mode_group.add_argument('--start', metavar='ENTITY',
                           help='Extract paths from specific entity')
    mode_group.add_argument('--golden-path', nargs=2, metavar=('START', 'END'),
                           help='Extract golden path between entities')
    mode_group.add_argument('--pattern', metavar='RELS',
                           help='Extract paths matching pattern (comma-separated)')
    
    # Parameters
    parser.add_argument('--length', type=int, default=2,
                       help='Path length (default: 2)')
    parser.add_argument('--count', type=int, default=100,
                       help='Number of paths/questions (default: 100)')
    parser.add_argument('--max-length', type=int, default=4,
                       help='Max length for golden path (default: 4)')
    
    # Output
    parser.add_argument('--output', help='Output JSON file')
    parser.add_argument('--format', choices=['full', 'questions', 'paths'],
                       default='full', help='Output format')
    parser.add_argument('--verbose', '-v', action='store_true')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(levelname)s: %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # Create pipeline
    try:
        pipeline = QuestionPipeline(args.uri, args.user, args.password)
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {e}")
        return 1
    
    try:
        # Run pipeline based on mode
        if args.random:
            logger.info(f"Running random extraction: {args.count} {args.length}-hop paths")
            results = pipeline.run_random(args.length, args.count)
        
        elif args.start:
            logger.info(f"Extracting from '{args.start}': {args.count} {args.length}-hop paths")
            results = pipeline.run_from_entity(args.start, args.length, args.count)
        
        elif args.golden_path:
            start, end = args.golden_path
            logger.info(f"Finding golden path: '{start}' → '{end}'")
            results = pipeline.run_golden_path(start, end, args.max_length)
        
        elif args.pattern:
            pattern_list = [p.strip() for p in args.pattern.split(',')]
            logger.info(f"Pattern extraction: {pattern_list}, count={args.count}")
            results = pipeline.run_pattern(pattern_list, args.count)
        
        # Filter successful results
        successful = [r for r in results if r.get('success', False)]
        failed = len(results) - len(successful)
        
        logger.info(f"Generated {len(successful)} questions ({failed} failed)")
        
        # Format output
        if args.format == 'questions':
            output = [{"question": r["question"], "path": r["display"]} 
                     for r in successful]
        elif args.format == 'paths':
            output = [{"typed_path": r["typed_path"], "instance_path": r["instance_path"]} 
                     for r in successful]
        else:  # full
            output = successful
        
        # Save or print
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(output, f, indent=2)
            logger.info(f"Results written to {args.output}")
        else:
            print(f"\n{'=' * 80}")
            print(f"Generated {len(successful)} Questions")
            print(f"{'=' * 80}\n")
            
            for i, result in enumerate(successful[:10], 1):  # Show first 10
                print(f"[{i}] Path: {result['display']}")
                print(f"    Question: {result['question']}")
                print()
            
            if len(successful) > 10:
                print(f"... and {len(successful) - 10} more")
                print(f"\nUse --output to save all results to a file")
        
        return 0
    
    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=args.verbose)
        return 1
    finally:
        pipeline.close()


if __name__ == "__main__":
    sys.exit(main())