#!/usr/bin/env python3
"""
kg_workflow.py

End-to-end workflow: Extract paths from KG -> Generate questions

Combines kg_path_extractor.py and kg_path_question_generator.py
for a seamless path-to-question pipeline.

Author: KG Workflow
Version: 1.0
"""

import argparse
import json
import logging
import sys
from pathlib import Path as FilePath
from typing import List, Dict

# Import from our modules
from kg_path_extractor import KnowledgeGraphIndex, PathFinder, KGQueryEngine
from kg_path_question_generator import KGQuestionGenerator


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(levelname)s: %(message)s'
    )


def extract_paths(
    kg_file: str,
    query_type: str,
    **kwargs
) -> List[List[str]]:
    """
    Extract paths from KG.
    
    Returns list of schema paths suitable for question generation.
    """
    logger = logging.getLogger(__name__)
    
    # Load KG
    kg = KnowledgeGraphIndex()
    kg.load_from_file(FilePath(kg_file))
    
    # Create query engine
    query_engine = KGQueryEngine(kg)
    
    # Execute query based on type
    if query_type == 'find_paths':
        paths = query_engine.query(
            'find_paths',
            start=kwargs['start'],
            end=kwargs['end'],
            max_length=kwargs.get('max_length', 3),
            limit=kwargs.get('limit')
        )
    
    elif query_type == 'pattern':
        paths = query_engine.query(
            'pattern_match',
            pattern=kwargs['pattern'],
            limit=kwargs.get('limit')
        )
    
    elif query_type == 'n_hop':
        paths = query_engine.query(
            'n_hop',
            start=kwargs['start'],
            length=kwargs['length'],
            limit=kwargs.get('limit')
        )
    
    else:
        raise ValueError(f"Unsupported query type: {query_type}")
    
    logger.info(f"Extracted {len(paths)} path(s)")
    
    # Convert to schema paths
    schema_paths = [path.to_schema_path() for path in paths]
    
    return schema_paths


def generate_questions(schema_paths: List[List[str]]) -> List[Dict]:
    """Generate questions from schema paths."""
    logger = logging.getLogger(__name__)
    
    generator = KGQuestionGenerator()
    results = generator.generate_batch(schema_paths, skip_invalid=True)
    
    successful = sum(1 for r in results if r['success'])
    logger.info(f"Generated {successful} question(s) from {len(schema_paths)} path(s)")
    
    return results


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Extract paths from KG and generate questions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Find paths and generate questions
  %(prog)s --kg kg.txt --find-paths --start "Kismet" --end "Josef von Sternberg"
  
  # N-hop exploration with questions
  %(prog)s --kg kg.txt --n-hop --start "Kismet" --length 2 --limit 10
  
  # Pattern matching with questions
  %(prog)s --kg kg.txt --pattern "directed_by,starred_actors" --limit 20
  
  # Save full results
  %(prog)s --kg kg.txt --n-hop --start "Kismet" --length 2 --output results.json
        '''
    )
    
    # Input
    parser.add_argument(
        '--kg',
        required=True,
        help='KG file (subject|relation|object format)'
    )
    
    # Query type
    query_group = parser.add_mutually_exclusive_group(required=True)
    query_group.add_argument(
        '--find-paths',
        action='store_true',
        help='Find paths between entities'
    )
    query_group.add_argument(
        '--pattern',
        type=str,
        help='Match relation pattern (comma-separated)'
    )
    query_group.add_argument(
        '--n-hop',
        action='store_true',
        help='Find N-hop paths from entity'
    )
    
    # Query parameters
    parser.add_argument('--start', help='Starting entity')
    parser.add_argument('--end', help='Ending entity')
    parser.add_argument('--length', type=int, help='Path length for N-hop')
    parser.add_argument('--max-length', type=int, default=3, help='Max path length')
    parser.add_argument('--limit', type=int, help='Max results')
    
    # Output
    parser.add_argument(
        '--output',
        help='Output JSON file'
    )
    parser.add_argument(
        '--paths-only',
        action='store_true',
        help='Output only paths (no questions)'
    )
    parser.add_argument(
        '--questions-only',
        action='store_true',
        help='Output only questions (no paths)'
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
    
    try:
        # Determine query type and parameters
        if args.find_paths:
            if not args.start or not args.end:
                logger.error("--find-paths requires --start and --end")
                return 1
            
            query_type = 'find_paths'
            query_kwargs = {
                'start': args.start,
                'end': args.end,
                'max_length': args.max_length,
                'limit': args.limit
            }
        
        elif args.pattern:
            pattern = [r.strip() for r in args.pattern.split(',')]
            query_type = 'pattern'
            query_kwargs = {
                'pattern': pattern,
                'limit': args.limit
            }
        
        elif args.n_hop:
            if not args.start or not args.length:
                logger.error("--n-hop requires --start and --length")
                return 1
            
            query_type = 'n_hop'
            query_kwargs = {
                'start': args.start,
                'length': args.length,
                'limit': args.limit
            }
        
        # Extract paths
        logger.info("Extracting paths from KG...")
        schema_paths = extract_paths(args.kg, query_type, **query_kwargs)
        
        if not schema_paths:
            logger.warning("No paths found")
            return 0
        
        # Generate questions (unless paths-only)
        questions_results = None
        if not args.paths_only:
            logger.info("Generating questions...")
            questions_results = generate_questions(schema_paths)
        
        # Prepare output
        output_data = []
        
        for i, schema_path in enumerate(schema_paths):
            item = {
                'index': i,
                'path': schema_path,
                'path_display': ' -> '.join(schema_path)
            }
            
            if questions_results and i < len(questions_results):
                result = questions_results[i]
                if result['success']:
                    item['question'] = result['question']
                else:
                    item['error'] = result['error']
            
            output_data.append(item)
        
        # Output results
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(output_data, f, indent=2)
            logger.info(f"Results written to {args.output}")
        else:
            # Print to console
            print(f"\n{'=' * 80}")
            print(f"Found {len(output_data)} path(s)")
            print(f"{'=' * 80}\n")
            
            for item in output_data:
                print(f"[{item['index'] + 1}] Path: {item['path_display']}")
                
                if 'question' in item:
                    if not args.paths_only:
                        print(f"    Question: {item['question']}")
                
                if 'error' in item:
                    print(f"    Error: {item['error']}")
                
                print()
        
        return 0
    
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=args.verbose)
        return 1


if __name__ == "__main__":
    sys.exit(main())