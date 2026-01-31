#!/usr/bin/env python3
"""
kg_path_question_generator.py

Generate structured natural-language questions from Knowledge Graph paths.
Supports 1-hop, 2-hop, 3-hop, and N-hop paths with comprehensive error handling.

Path format: [node_type, relation, node_type, relation, node_type, ...]
Example: ["title", "directed_by", "person_name", "starred_actors", "title"]

Author: KG Question Generator
Version: 2.0
"""

import argparse
import json
import sys
import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field


# ============================================================
# CONFIGURATION
# ============================================================

@dataclass
class GeneratorConfig:
    """Configuration for question generation with validation."""
    
    node_phrases: Dict[str, str] = field(default_factory=lambda: {
        "title": "movies",
        "person_name": "people",
        "genre": "genres",
        "year": "years",
        "language": "languages",
        "tag": "tags",
        "number": "numbers",
        "unknown": "entities"
    })
    
    bound_node_phrases: Dict[str, str] = field(default_factory=lambda: {
        "title": "the movie {title}",
        "person_name": "{person}",
        "genre": "the genre {genre}",
        "year": "the year {year}",
        "language": "the language {language}",
        "tag": "the tag {tag}",
        "number": "the number {number}",
        "unknown": "the entity {entity}"
    })
    
    relation_clauses: Dict[str, str] = field(default_factory=lambda: {
        "directed_by": "directed by",
        "written_by": "written by",
        "starred_actors": "starring",
        "has_genre": "with the genre",
        "release_year": "released in",
        "in_language": "in the language",
        "has_tags": "tagged with",
        "has_imdb_rating": "with IMDb rating",
        "has_imdb_votes": "with IMDb votes"
    })
    
    wh_words: Dict[str, str] = field(default_factory=lambda: {
        "person_name": "Who",
        "title": "Which movies",
        "genre": "What genres",
        "year": "In which years",
        "language": "What languages",
        "tag": "Which tags",
        "number": "What numbers",
        "unknown": "What entities"
    })
    
    grammar_replacements: Dict[str, str] = field(default_factory=lambda: {
        # Core relationship normalizations
        "people directed by": "directors of",
        "people written by": "writers of",
        "people starring": "actors in",
        "people who directed the movie": "the director of the movie",
        "people who wrote the movie": "the writer of the movie",
        "people who starred in the movie": "the actors in the movie",
        
        # Movie-to-movie normalizations
        "movies directed by the movie": "movies directed by",
        "movies written by the movie": "movies written by",
        "movies starring the movie": "movies starring",
        "people who starred in movies": "actors in movies",
        
        # Genre normalizations
        "genres with the genre": "genres",
        "genres of movies directed by": "genres of movies directed by",
        "genres of movies written by": "genres of movies written by",
        "genres of movies starring": "genres of movies starring",
        
        # Year normalizations
        "years released in": "years of release for",
        "years released in the year": "years",
        "released in the year": "released in",
        
        # Language normalizations
        "languages in the language": "languages",
        "in the language the language": "in the language",
        
        # Tag normalizations
        "tags tagged with": "tags for",
        "with the tag the tag": "with the tag",
        "tagged with the tag": "tagged with",
        
        # Unknown normalizations
        "entities directed by": "entities that directed",
        "entities written by": "entities that wrote",
        "entities starring": "entities that starred in",
        
        # Cleanup rules (applied last)
        "the the": "the",
        "  ": " "  # Double space cleanup
    })


# ============================================================
# CORE GENERATOR CLASS
# ============================================================

class KGQuestionGenerator:
    """Generate natural language questions from KG paths."""
    
    def __init__(self, config: Optional[GeneratorConfig] = None):
        """
        Initialize the question generator.
        
        Args:
            config: Optional custom configuration. Uses defaults if None.
        """
        self.config = config or GeneratorConfig()
        self.logger = logging.getLogger(__name__)
    
    def validate_path(self, path: List[str]) -> Tuple[bool, Optional[str]]:
        """
        Validate a KG path for correctness.
        
        Args:
            path: List representing the KG path
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check minimum length
        if len(path) < 3:
            return False, "Path must have at least 3 elements (start node, relation, end node)"
        
        # Check odd length (alternating nodes and relations)
        if len(path) % 2 == 0:
            return False, "Path must have odd length (nodes and relations alternate)"
        
        # Validate node types (even indices)
        for i in range(0, len(path), 2):
            node_type = path[i]
            if node_type not in self.config.node_phrases:
                return False, f"Unknown node type '{node_type}' at position {i}"
        
        # Validate relations (odd indices)
        for i in range(1, len(path), 2):
            relation = path[i]
            if relation not in self.config.relation_clauses:
                return False, f"Unknown relation '{relation}' at position {i}"
        
        return True, None
    
    def generate_question(self, path: List[str], validate: bool = True) -> str:
        """
        Generate a structured question from a KG path.
        
        Args:
            path: List representing the KG path [node, rel, node, rel, ...]
            validate: Whether to validate the path before generation
            
        Returns:
            Natural-language question string
            
        Raises:
            ValueError: If path is invalid and validate=True
        """
        if validate:
            is_valid, error_msg = self.validate_path(path)
            if not is_valid:
                raise ValueError(f"Invalid path: {error_msg}")
        
        start_node = path[0]
        end_node = path[-1]
        
        # Get WH-word for the target (end) node
        wh_word = self.config.wh_words.get(end_node, "What")
        
        # Get the bound phrase for the starting node
        clause = self.config.bound_node_phrases.get(
            start_node, 
            f"the {start_node.replace('_', ' ')} {{item}}"
        )
        
        # Build nested relative clauses by iterating through path
        for i in range(1, len(path) - 1, 2):
            relation = path[i]
            next_node = path[i + 1]
            
            node_phrase = self.config.node_phrases.get(next_node, "entities")
            relation_clause = self.config.relation_clauses.get(relation, relation.replace("_", " "))
            
            # Build the clause in the correct order
            clause = f"{node_phrase} {relation_clause} {clause}"
        
        # Normalize grammar
        clause = self._normalize_clause(clause)
        
        # Construct final question
        question = f"{wh_word} are associated with {clause}?"
        
        return question
    
    def _normalize_clause(self, text: str) -> str:
        """
        Apply grammar normalization rules to clean up the clause.
        
        Args:
            text: Raw clause text
            
        Returns:
            Normalized clause text
        """
        normalized = text
        
        # Apply all grammar replacement rules
        for pattern, replacement in self.config.grammar_replacements.items():
            normalized = normalized.replace(pattern, replacement)
        
        # Trim whitespace
        normalized = " ".join(normalized.split())
        
        return normalized
    
    def generate_batch(
        self, 
        paths: List[List[str]], 
        skip_invalid: bool = False
    ) -> List[Dict[str, any]]:
        """
        Generate questions for multiple paths.
        
        Args:
            paths: List of KG paths
            skip_invalid: If True, skip invalid paths; if False, raise on invalid
            
        Returns:
            List of dicts with 'path', 'question', and optional 'error' keys
        """
        results = []
        
        for idx, path in enumerate(paths):
            result = {
                'path': path,
                'index': idx
            }
            
            try:
                question = self.generate_question(path, validate=True)
                result['question'] = question
                result['success'] = True
            except ValueError as e:
                result['success'] = False
                result['error'] = str(e)
                
                if not skip_invalid:
                    raise
                else:
                    self.logger.warning(f"Skipping invalid path at index {idx}: {e}")
            
            results.append(result)
        
        return results


# ============================================================
# SCHEMA LOADER
# ============================================================

class KGSchemaLoader:
    """Load and parse KG schema files."""
    
    @staticmethod
    def load_schema(filepath: Path) -> List[Tuple[str, str, str, int]]:
        """
        Load a KG schema from a pipe-delimited file.
        
        Args:
            filepath: Path to the schema file
            
        Returns:
            List of tuples (subject_type, relation, object_type, frequency)
        """
        schema = []
        
        with open(filepath, 'r') as f:
            # Skip header
            next(f)
            
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                parts = line.split('|')
                if len(parts) == 4:
                    subject, relation, obj, freq = parts
                    schema.append((subject, relation, obj, int(freq)))
        
        return schema
    
    @staticmethod
    def get_valid_relations(schema: List[Tuple[str, str, str, int]]) -> Dict[str, List[Tuple[str, str]]]:
        """
        Extract valid relations from schema.
        
        Args:
            schema: Loaded schema data
            
        Returns:
            Dict mapping node_type to list of (relation, target_node_type) tuples
        """
        relations = {}
        
        for subject, relation, obj, _ in schema:
            if subject not in relations:
                relations[subject] = []
            relations[subject].append((relation, obj))
        
        return relations


# ============================================================
# CLI INTERFACE
# ============================================================

def setup_logging(verbose: bool = False):
    """Configure logging based on verbosity level."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(levelname)s: %(message)s'
    )


def parse_path_arg(path_str: str) -> List[str]:
    """Parse path from command line argument."""
    # Try JSON format first
    try:
        path = json.loads(path_str)
        if isinstance(path, list):
            return path
    except json.JSONDecodeError:
        pass
    
    # Try comma-separated format
    return [p.strip() for p in path_str.split(',')]


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Generate natural language questions from Knowledge Graph paths',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Single path (JSON format)
  %(prog)s --path '["title", "directed_by", "person_name"]'
  
  # Single path (comma-separated)
  %(prog)s --path "title,directed_by,person_name"
  
  # Multiple paths from file
  %(prog)s --input paths.json --output questions.json
  
  # With schema validation
  %(prog)s --path "title,directed_by,person_name" --schema kg_schema.txt
  
  # Interactive mode
  %(prog)s --interactive
        '''
    )
    
    # Input options
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        '--path',
        type=str,
        help='Single KG path (JSON array or comma-separated)'
    )
    input_group.add_argument(
        '--input',
        type=Path,
        help='Input file with paths (JSON format)'
    )
    input_group.add_argument(
        '--interactive',
        action='store_true',
        help='Interactive mode for entering paths'
    )
    
    # Output options
    parser.add_argument(
        '--output',
        type=Path,
        help='Output file for results (JSON format)'
    )
    
    # Configuration options
    parser.add_argument(
        '--schema',
        type=Path,
        help='KG schema file for validation'
    )
    parser.add_argument(
        '--skip-invalid',
        action='store_true',
        help='Skip invalid paths instead of failing'
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Verbose output'
    )
    
    # Examples
    parser.add_argument(
        '--examples',
        action='store_true',
        help='Show example paths and questions'
    )
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # Show examples if requested
    if args.examples:
        show_examples()
        return 0
    
    # Initialize generator
    generator = KGQuestionGenerator()
    
    # Load schema if provided
    if args.schema:
        if not args.schema.exists():
            logger.error(f"Schema file not found: {args.schema}")
            return 1
        
        schema = KGSchemaLoader.load_schema(args.schema)
        logger.info(f"Loaded schema with {len(schema)} relations")
    
    # Process based on input mode
    if args.interactive:
        return run_interactive(generator)
    
    elif args.path:
        # Single path mode
        try:
            path = parse_path_arg(args.path)
            question = generator.generate_question(path)
            
            result = {
                'path': path,
                'question': question
            }
            
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(result, f, indent=2)
                logger.info(f"Question written to {args.output}")
            else:
                print(f"Path: {' -> '.join(path)}")
                print(f"Question: {question}")
            
            return 0
            
        except ValueError as e:
            logger.error(f"Invalid path: {e}")
            return 1
    
    elif args.input:
        # Batch mode
        if not args.input.exists():
            logger.error(f"Input file not found: {args.input}")
            return 1
        
        try:
            with open(args.input, 'r') as f:
                paths = json.load(f)
            
            if not isinstance(paths, list):
                logger.error("Input file must contain a JSON array of paths")
                return 1
            
            results = generator.generate_batch(paths, skip_invalid=args.skip_invalid)
            
            # Count successes and failures
            successful = sum(1 for r in results if r['success'])
            failed = len(results) - successful
            
            logger.info(f"Processed {len(results)} paths: {successful} successful, {failed} failed")
            
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(results, f, indent=2)
                logger.info(f"Results written to {args.output}")
            else:
                for result in results:
                    if result['success']:
                        print(f"✓ {' -> '.join(result['path'])}")
                        print(f"  {result['question']}\n")
                    else:
                        print(f"✗ {' -> '.join(result['path'])}")
                        print(f"  Error: {result['error']}\n")
            
            return 0 if failed == 0 else 1
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in input file: {e}")
            return 1
        except Exception as e:
            logger.error(f"Error processing input: {e}")
            return 1
    
    else:
        parser.print_help()
        return 1


def run_interactive(generator: KGQuestionGenerator) -> int:
    """Run interactive mode for path entry."""
    print("Interactive KG Question Generator")
    print("=" * 60)
    print("Enter paths as comma-separated values or JSON arrays.")
    print("Type 'quit' or 'exit' to stop, 'help' for examples.\n")
    
    while True:
        try:
            user_input = input("Enter path: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            if user_input.lower() == 'help':
                print("\nExample paths:")
                print('  title,directed_by,person_name')
                print('  ["title", "has_genre", "genre"]')
                print('  title,written_by,person_name,starred_actors,title\n')
                continue
            
            if not user_input:
                continue
            
            path = parse_path_arg(user_input)
            question = generator.generate_question(path)
            
            print(f"\n✓ Question: {question}\n")
            
        except ValueError as e:
            print(f"\n✗ Error: {e}\n")
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except EOFError:
            break
    
    return 0


def show_examples():
    """Display example paths and generated questions."""
    generator = KGQuestionGenerator()
    
    examples = [
        # 1-hop examples
        (["title", "directed_by", "person_name"], "1-hop: Movies to Directors"),
        (["title", "has_genre", "genre"], "1-hop: Movies to Genres"),
        (["person_name", "starred_actors", "title"], "1-hop: Actors to Movies"),
        
        # 2-hop examples
        (["title", "directed_by", "person_name", "starred_actors", "title"], 
         "2-hop: Movies via Directors who Acted"),
        (["title", "has_genre", "genre", "directed_by", "person_name"],
         "2-hop: Directors via Genre"),
        
        # 3-hop examples
        (["title", "written_by", "person_name", "directed_by", "title", "has_genre", "genre"],
         "3-hop: Genres via Writer-Director chain"),
        (["person_name", "directed_by", "title", "starred_actors", "person_name", "written_by", "title"],
         "3-hop: Movies via Director-Actor-Writer chain"),
    ]
    
    print("KG Question Generator - Examples")
    print("=" * 80)
    
    for path, description in examples:
        print(f"\n{description}")
        print(f"Path: {' → '.join(path)}")
        try:
            question = generator.generate_question(path)
            print(f"Question: {question}")
        except ValueError as e:
            print(f"Error: {e}")
        print("-" * 80)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    sys.exit(main())