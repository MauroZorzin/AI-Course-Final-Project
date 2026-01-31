import argparse
from typing import Dict, List, Tuple, Set
from collections import defaultdict


def parse_knowledge_graph(file_path: str) -> List[Tuple[str, str, str]]:
    """
    Parse the knowledge graph file.
    
    Args:
        file_path: Path to the input file
    
    Returns:
        List of tuples (subject, relationship, object)
    """
    triples = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            parts = line.split('|')
            if len(parts) != 3:
                continue
            
            triples.append((parts[0], parts[1], parts[2]))
    
    return triples


def verify_structure(original: List[Tuple[str, str, str]], 
                     anonymized: List[Tuple[str, str, str]]) -> Tuple[bool, List[str]]:
    """
    Verify that the structure of both graphs is identical.
    
    Args:
        original: Original knowledge graph triples
        anonymized: Anonymized knowledge graph triples
    
    Returns:
        Tuple of (success, list of error messages)
    """
    errors = []
    
    # Check same number of triples
    if len(original) != len(anonymized):
        errors.append(f"Different number of triples: {len(original)} vs {len(anonymized)}")
        return False, errors
    
    # Check each triple
    for i, (orig, anon) in enumerate(zip(original, anonymized)):
        orig_subj, orig_rel, orig_obj = orig
        anon_subj, anon_rel, anon_obj = anon
        
        # Subject should be unchanged
        if orig_subj != anon_subj:
            errors.append(f"Line {i+1}: Subject changed from '{orig_subj}' to '{anon_subj}'")
        
        # Relationship should be unchanged
        if orig_rel != anon_rel:
            errors.append(f"Line {i+1}: Relationship changed from '{orig_rel}' to '{anon_rel}'")
    
    success = len(errors) == 0
    return success, errors


def verify_consistency(original: List[Tuple[str, str, str]], 
                       anonymized: List[Tuple[str, str, str]]) -> Tuple[bool, Dict[str, str], List[str]]:
    """
    Verify that the replacement is consistent (same object always maps to same replacement).
    
    Args:
        original: Original knowledge graph triples
        anonymized: Anonymized knowledge graph triples
    
    Returns:
        Tuple of (success, mapping dictionary, list of error messages)
    """
    errors = []
    
    # Build mapping from original to anonymized
    mapping = {}
    reverse_mapping = defaultdict(set)
    
    for (orig_subj, orig_rel, orig_obj), (anon_subj, anon_rel, anon_obj) in zip(original, anonymized):
        # Check consistency
        if orig_obj in mapping:
            if mapping[orig_obj] != anon_obj:
                errors.append(
                    f"Inconsistent mapping: '{orig_obj}' mapped to both "
                    f"'{mapping[orig_obj]}' and '{anon_obj}'"
                )
        else:
            mapping[orig_obj] = anon_obj
        
        # Check reverse mapping (one-to-one relationship)
        reverse_mapping[anon_obj].add(orig_obj)
    
    # Check that each replacement maps to only one original
    for anon_obj, orig_objs in reverse_mapping.items():
        if len(orig_objs) > 1:
            errors.append(
                f"Multiple original objects mapped to '{anon_obj}': {orig_objs}"
            )
    
    success = len(errors) == 0
    return success, mapping, errors


def verify_objects_changed(original: List[Tuple[str, str, str]], 
                           anonymized: List[Tuple[str, str, str]]) -> Tuple[bool, List[str]]:
    """
    Verify that objects were actually changed.
    
    Args:
        original: Original knowledge graph triples
        anonymized: Anonymized knowledge graph triples
    
    Returns:
        Tuple of (success, list of warnings)
    """
    warnings = []
    unchanged_count = 0
    
    for (orig_subj, orig_rel, orig_obj), (anon_subj, anon_rel, anon_obj) in zip(original, anonymized):
        if orig_obj == anon_obj:
            unchanged_count += 1
    
    if unchanged_count == len(original):
        warnings.append("WARNING: No objects were changed!")
        return False, warnings
    
    if unchanged_count > 0:
        warnings.append(f"INFO: {unchanged_count} objects remained unchanged")
    
    return True, warnings


def print_statistics(original: List[Tuple[str, str, str]], 
                    anonymized: List[Tuple[str, str, str]],
                    mapping: Dict[str, str]) -> None:
    """
    Print statistics about the anonymization.
    
    Args:
        original: Original knowledge graph triples
        anonymized: Anonymized knowledge graph triples
        mapping: Dictionary of original to anonymized mappings
    """
    orig_objects = set(triple[2] for triple in original)
    anon_objects = set(triple[2] for triple in anonymized)
    
    print("\n" + "="*60)
    print("STATISTICS")
    print("="*60)
    print(f"Total triples: {len(original)}")
    print(f"Unique objects in original: {len(orig_objects)}")
    print(f"Unique objects in anonymized: {len(anon_objects)}")
    print(f"Unique mappings created: {len(mapping)}")
    
    # Count how many times each object appears
    orig_counts = defaultdict(int)
    anon_counts = defaultdict(int)
    
    for triple in original:
        orig_counts[triple[2]] += 1
    
    for triple in anonymized:
        anon_counts[triple[2]] += 1
    
    print(f"\nMost frequent original objects:")
    for obj, count in sorted(orig_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
        replacement = mapping.get(obj, "N/A")
        print(f"  '{obj}' -> '{replacement}' (appears {count} times)")


def main():
    parser = argparse.ArgumentParser(
        description='Verify knowledge graph anonymization'
    )
    parser.add_argument('original_file', help='Original knowledge graph file')
    parser.add_argument('anonymized_file', help='Anonymized knowledge graph file')
    parser.add_argument('--verbose', action='store_true',
                       help='Show detailed error messages')
    
    args = parser.parse_args()
    
    print("="*60)
    print("KNOWLEDGE GRAPH ANONYMIZATION VERIFICATION")
    print("="*60)
    
    print(f"\nLoading original graph from: {args.original_file}")
    original_triples = parse_knowledge_graph(args.original_file)
    print(f"Loaded {len(original_triples)} triples")
    
    print(f"\nLoading anonymized graph from: {args.anonymized_file}")
    anonymized_triples = parse_knowledge_graph(args.anonymized_file)
    print(f"Loaded {len(anonymized_triples)} triples")
    
    all_passed = True
    mapping = {}
    
    # Test 1: Structure verification
    print("\n" + "-"*60)
    print("TEST 1: Structure Verification")
    print("-"*60)
    structure_ok, structure_errors = verify_structure(original_triples, anonymized_triples)
    
    if structure_ok:
        print("✓ PASSED: Structure is intact (subjects and relationships unchanged)")
    else:
        print("✗ FAILED: Structure has been modified")
        all_passed = False
        if args.verbose:
            for error in structure_errors[:10]:  # Show first 10 errors
                print(f"  - {error}")
            if len(structure_errors) > 10:
                print(f"  ... and {len(structure_errors) - 10} more errors")
        else:
            print(f"  Found {len(structure_errors)} errors (use --verbose to see details)")
    
    # Test 2: Consistency verification
    print("\n" + "-"*60)
    print("TEST 2: Consistency Verification")
    print("-"*60)
    consistency_ok, mapping, consistency_errors = verify_consistency(original_triples, anonymized_triples)
    
    if consistency_ok:
        print("✓ PASSED: All object replacements are consistent")
        print(f"  Created {len(mapping)} unique one-to-one mappings")
    else:
        print("✗ FAILED: Inconsistent object replacements detected")
        all_passed = False
        if args.verbose:
            for error in consistency_errors[:10]:
                print(f"  - {error}")
            if len(consistency_errors) > 10:
                print(f"  ... and {len(consistency_errors) - 10} more errors")
        else:
            print(f"  Found {len(consistency_errors)} errors (use --verbose to see details)")
    
    # Test 3: Verify objects were actually changed
    print("\n" + "-"*60)
    print("TEST 3: Object Change Verification")
    print("-"*60)
    changed_ok, warnings = verify_objects_changed(original_triples, anonymized_triples)
    
    if changed_ok:
        print("✓ PASSED: Objects have been successfully replaced")
        changed_count = len([1 for (o, a) in zip(original_triples, anonymized_triples) if o[2] != a[2]])
        print(f"  {changed_count} out of {len(original_triples)} triples have modified objects")
    else:
        print("✗ FAILED: Objects were not changed")
        all_passed = False
    
    if warnings:
        for warning in warnings:
            print(f"  {warning}")
    
    # Print statistics if consistency check passed
    if consistency_ok and mapping:
        print_statistics(original_triples, anonymized_triples, mapping)
    
    # Final summary
    print("\n" + "="*60)
    print("FINAL RESULT")
    print("="*60)
    
    if all_passed:
        print("✓ ALL TESTS PASSED")
        print("\nThe anonymization was performed correctly:")
        print("  • Structure preserved (subjects and relationships unchanged)")
        print("  • Consistent one-to-one mapping of objects")
        print("  • Objects successfully replaced with random strings")
    else:
        print("✗ SOME TESTS FAILED")
        print("\nPlease review the errors above and re-run the anonymization.")
    
    print("="*60)
    
    # Return exit code
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())