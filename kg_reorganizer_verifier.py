import argparse
from typing import Dict, List, Tuple, Set
from collections import defaultdict, Counter
from pathlib import Path


class KnowledgeGraphVerifier:
    """Verify consistency of reorganized knowledge graphs"""
    
    def __init__(self):
        self.original_triples: List[Tuple[str, str, str]] = []
        self.reorganized_triples: List[Tuple[str, str, str]] = []
        self.mapping: Dict[str, str] = {}
        
        # For analysis
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
    
    def parse_triples(self, file_path: str) -> List[Tuple[str, str, str]]:
        """Parse knowledge graph file"""
        triples = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                parts = line.split('|')
                if len(parts) != 3:
                    self.warnings.append(f"Line {line_num} has incorrect format: {line}")
                    continue
                
                triples.append((parts[0].strip(), parts[1].strip(), parts[2].strip()))
        
        return triples
    
    def parse_mapping(self, file_path: str) -> Dict[str, str]:
        """Parse mapping file"""
        mapping = {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
                # Skip header if present
                start_idx = 0
                if lines and '|' in lines[0] and ('Original' in lines[0] or 'Swapped' in lines[0]):
                    start_idx = 1
                
                for line_num, line in enumerate(lines[start_idx:], start_idx + 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    parts = line.split('|')
                    if len(parts) >= 2:
                        original = parts[0].strip()
                        swapped = parts[1].strip()
                        mapping[original] = swapped
                    else:
                        self.warnings.append(f"Mapping line {line_num} has incorrect format: {line}")
        
        except FileNotFoundError:
            self.warnings.append(f"Mapping file not found: {file_path}")
            return {}
        
        return mapping
    
    def verify_triple_count(self) -> bool:
        """Verify that triple counts match"""
        if len(self.original_triples) != len(self.reorganized_triples):
            self.errors.append(
                f"Triple count mismatch: Original has {len(self.original_triples)} triples, "
                f"Reorganized has {len(self.reorganized_triples)} triples"
            )
            return False
        
        self.info.append(f"✓ Triple count matches: {len(self.original_triples)} triples")
        return True
    
    def verify_relationship_preservation(self) -> bool:
        """Verify that relationships are preserved (unless explicitly swapped)"""
        original_rels = Counter(rel for _, rel, _ in self.original_triples)
        reorganized_rels = Counter(rel for _, rel, _ in self.reorganized_triples)
        
        # Check if relationship counts changed
        if original_rels != reorganized_rels:
            # If relationships were meant to be preserved, this is an error
            missing_rels = original_rels - reorganized_rels
            extra_rels = reorganized_rels - original_rels
            
            if missing_rels or extra_rels:
                self.warnings.append("Relationship distribution changed:")
                if missing_rels:
                    self.warnings.append(f"  Missing: {dict(missing_rels)}")
                if extra_rels:
                    self.warnings.append(f"  Added: {dict(extra_rels)}")
                return False
        
        self.info.append(f"✓ Relationship distribution preserved: {len(original_rels)} unique relationships")
        return True
    
    def verify_consistency(self) -> bool:
        """Verify that entity swaps are consistent across all triples"""
        # Build a mapping from what we observe in the data
        observed_mapping = {}
        inconsistencies = []
        
        for (orig_subj, orig_rel, orig_obj), (reorg_subj, reorg_rel, reorg_obj) in zip(
            self.original_triples, self.reorganized_triples
        ):
            # Check subject consistency
            if orig_subj in observed_mapping:
                if observed_mapping[orig_subj] != reorg_subj:
                    inconsistencies.append(
                        f"Subject '{orig_subj}' maps to both '{observed_mapping[orig_subj]}' "
                        f"and '{reorg_subj}'"
                    )
            else:
                observed_mapping[orig_subj] = reorg_subj
            
            # Check object consistency
            if orig_obj in observed_mapping:
                if observed_mapping[orig_obj] != reorg_obj:
                    inconsistencies.append(
                        f"Object '{orig_obj}' maps to both '{observed_mapping[orig_obj]}' "
                        f"and '{reorg_obj}'"
                    )
            else:
                observed_mapping[orig_obj] = reorg_obj
            
            # Check relationship consistency
            if orig_rel in observed_mapping:
                if observed_mapping[orig_rel] != reorg_rel:
                    inconsistencies.append(
                        f"Relationship '{orig_rel}' maps to both '{observed_mapping[orig_rel]}' "
                        f"and '{reorg_rel}'"
                    )
            else:
                observed_mapping[orig_rel] = reorg_rel
        
        if inconsistencies:
            self.errors.append("Consistency check FAILED:")
            for inc in inconsistencies[:10]:  # Show first 10
                self.errors.append(f"  - {inc}")
            if len(inconsistencies) > 10:
                self.errors.append(f"  ... and {len(inconsistencies) - 10} more inconsistencies")
            return False
        
        self.info.append(f"✓ Consistency verified: All {len(observed_mapping)} entities map consistently")
        return True
    
    def verify_structure_preservation(self) -> bool:
        """Verify that the graph structure is preserved"""
        # Build adjacency structure for both graphs
        def build_structure(triples):
            structure = defaultdict(lambda: defaultdict(set))
            for subj, rel, obj in triples:
                structure[subj][rel].add(obj)
            return structure
        
        orig_structure = build_structure(self.original_triples)
        reorg_structure = build_structure(self.reorganized_triples)
        
        # Check that structure sizes match
        if len(orig_structure) != len(reorg_structure):
            self.errors.append(
                f"Structure mismatch: Original has {len(orig_structure)} subjects, "
                f"Reorganized has {len(reorg_structure)} subjects"
            )
            return False
        
        # Check that each subject has the same relationships
        for orig_subj, orig_rels in orig_structure.items():
            # Find what this subject maps to
            mapped_subj = None
            for (o_subj, _, _), (r_subj, _, _) in zip(self.original_triples, self.reorganized_triples):
                if o_subj == orig_subj:
                    mapped_subj = r_subj
                    break
            
            if mapped_subj is None:
                self.errors.append(f"Subject '{orig_subj}' not found in reorganized graph")
                return False
            
            reorg_rels = reorg_structure.get(mapped_subj, {})
            
            # Check relationship types
            if set(orig_rels.keys()) != set(reorg_rels.keys()):
                self.errors.append(
                    f"Relationship types differ for subject '{orig_subj}' (→ '{mapped_subj}')"
                )
                return False
            
            # Check relationship counts
            for rel in orig_rels:
                if len(orig_rels[rel]) != len(reorg_rels[rel]):
                    self.errors.append(
                        f"Relationship '{rel}' count differs for subject '{orig_subj}' "
                        f"(Original: {len(orig_rels[rel])}, Reorganized: {len(reorg_rels[rel])})"
                    )
                    return False
        
        self.info.append("✓ Graph structure preserved: All subjects have same relationships")
        return True
    
    def verify_mapping_coverage(self) -> bool:
        """Verify that the mapping file covers all swapped entities"""
        if not self.mapping:
            self.warnings.append("No mapping file provided, skipping mapping verification")
            return True
        
        # Extract all entities from both graphs
        original_entities = set()
        reorganized_entities = set()
        
        for subj, rel, obj in self.original_triples:
            original_entities.update([subj, rel, obj])
        
        for subj, rel, obj in self.reorganized_triples:
            reorganized_entities.update([subj, rel, obj])
        
        # Check that mapping includes all changed entities
        changed_entities = set()
        for orig, reorg in zip(self.original_triples, self.reorganized_triples):
            for o_entity, r_entity in zip(orig, reorg):
                if o_entity != r_entity:
                    changed_entities.add(o_entity)
        
        # Check coverage
        mapped_entities = set(self.mapping.keys())
        missing_from_mapping = changed_entities - mapped_entities
        
        if missing_from_mapping:
            self.warnings.append(
                f"Mapping file missing {len(missing_from_mapping)} changed entities:"
            )
            for entity in list(missing_from_mapping)[:5]:
                self.warnings.append(f"  - {entity}")
            if len(missing_from_mapping) > 5:
                self.warnings.append(f"  ... and {len(missing_from_mapping) - 5} more")
        else:
            self.info.append(f"✓ Mapping covers all {len(changed_entities)} changed entities")
        
        return len(missing_from_mapping) == 0
    
    def verify_type_consistency(self) -> bool:
        """Verify that entity types are preserved (numbers with numbers, names with names, etc.)"""
        type_errors = []
        
        def is_number(s):
            try:
                float(s)
                return True
            except:
                return False
        
        def is_year(s):
            try:
                num = int(float(s))
                return 1800 <= num <= 2100
            except:
                return False
        
        def has_capitals(s):
            return any(c.isupper() for c in s)
        
        # Check consistency across swaps
        for (o_subj, o_rel, o_obj), (r_subj, r_rel, r_obj) in zip(
            self.original_triples, self.reorganized_triples
        ):
            # Check subjects
            if o_subj != r_subj:
                if is_number(o_subj) != is_number(r_subj):
                    type_errors.append(f"Number/non-number swap: '{o_subj}' ↔ '{r_subj}'")
                elif is_year(o_subj) and not is_year(r_subj):
                    type_errors.append(f"Year swapped with non-year: '{o_subj}' ↔ '{r_subj}'")
            
            # Check objects
            if o_obj != r_obj:
                if is_number(o_obj) != is_number(r_obj):
                    type_errors.append(f"Number/non-number swap: '{o_obj}' ↔ '{r_obj}'")
                elif is_year(o_obj) and not is_year(r_obj):
                    type_errors.append(f"Year swapped with non-year: '{o_obj}' ↔ '{r_obj}'")
        
        if type_errors:
            self.warnings.append("Type consistency issues found:")
            for error in type_errors[:10]:
                self.warnings.append(f"  - {error}")
            if len(type_errors) > 10:
                self.warnings.append(f"  ... and {len(type_errors) - 10} more")
            return False
        
        self.info.append("✓ Type consistency maintained: Numbers with numbers, years with years")
        return True
    
    def verify_no_duplicates(self) -> bool:
        """Verify no duplicate triples exist"""
        orig_duplicates = len(self.original_triples) - len(set(self.original_triples))
        reorg_duplicates = len(self.reorganized_triples) - len(set(self.reorganized_triples))
        
        if orig_duplicates > 0:
            self.warnings.append(f"Original graph has {orig_duplicates} duplicate triples")
        
        if reorg_duplicates > 0:
            self.warnings.append(f"Reorganized graph has {reorg_duplicates} duplicate triples")
        
        if orig_duplicates == 0 and reorg_duplicates == 0:
            self.info.append("✓ No duplicate triples found")
            return True
        
        return orig_duplicates == 0 and reorg_duplicates == 0
    
    def verify_bijection(self) -> bool:
        """Verify that the mapping is a proper bijection (one-to-one)"""
        if not self.mapping:
            return True
        
        # Check that mapping is injective (one-to-one)
        reverse_mapping = defaultdict(set)
        for orig, swapped in self.mapping.items():
            reverse_mapping[swapped].add(orig)
        
        # Find entities that multiple originals map to
        collisions = {k: v for k, v in reverse_mapping.items() if len(v) > 1}
        
        if collisions:
            self.errors.append("Mapping is not one-to-one (bijection violated):")
            for swapped, originals in list(collisions.items())[:5]:
                self.errors.append(f"  '{swapped}' ← {originals}")
            if len(collisions) > 5:
                self.errors.append(f"  ... and {len(collisions) - 5} more collisions")
            return False
        
        self.info.append("✓ Mapping is a proper bijection (one-to-one)")
        return True
    
    def run_all_verifications(self, original_file: str, reorganized_file: str, 
                             mapping_file: str = None) -> bool:
        """Run all verification checks"""
        print("="*70)
        print("KNOWLEDGE GRAPH REORGANIZATION VERIFICATION")
        print("="*70)
        print()
        
        # Load files
        print("Loading files...")
        self.original_triples = self.parse_triples(original_file)
        self.reorganized_triples = self.parse_triples(reorganized_file)
        
        if mapping_file:
            self.mapping = self.parse_mapping(mapping_file)
            print(f"Loaded {len(self.original_triples)} original triples")
            print(f"Loaded {len(self.reorganized_triples)} reorganized triples")
            print(f"Loaded {len(self.mapping)} mappings")
        else:
            print(f"Loaded {len(self.original_triples)} original triples")
            print(f"Loaded {len(self.reorganized_triples)} reorganized triples")
            print("No mapping file provided")
        
        print()
        print("Running verification checks...")
        print("-"*70)
        
        # Run all checks
        all_passed = True
        
        checks = [
            ("Triple Count", self.verify_triple_count),
            ("Relationship Preservation", self.verify_relationship_preservation),
            ("Entity Consistency", self.verify_consistency),
            ("Structure Preservation", self.verify_structure_preservation),
            ("Type Consistency", self.verify_type_consistency),
            ("No Duplicates", self.verify_no_duplicates),
        ]
        
        if mapping_file:
            checks.extend([
                ("Mapping Coverage", self.verify_mapping_coverage),
                ("Bijection Property", self.verify_bijection),
            ])
        
        for check_name, check_func in checks:
            print(f"\n[{check_name}]")
            result = check_func()
            all_passed = all_passed and result
        
        # Print results
        print()
        print("="*70)
        print("VERIFICATION RESULTS")
        print("="*70)
        
        if self.info:
            print("\n✓ PASSED CHECKS:")
            for info in self.info:
                print(f"  {info}")
        
        if self.warnings:
            print("\n⚠ WARNINGS:")
            for warning in self.warnings:
                print(f"  {warning}")
        
        if self.errors:
            print("\n✗ ERRORS:")
            for error in self.errors:
                print(f"  {error}")
        
        print()
        print("="*70)
        if all_passed and not self.errors:
            print("✓ ALL VERIFICATIONS PASSED")
            print("The reorganized graph is consistent and valid!")
        elif self.errors:
            print("✗ VERIFICATION FAILED")
            print("Critical errors found - please review the reorganization.")
        else:
            print("⚠ VERIFICATION PASSED WITH WARNINGS")
            print("The reorganization is valid but has minor issues.")
        print("="*70)
        
        return all_passed and not self.errors
    
    def save_report(self, output_file: str):
        """Save verification report to file"""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("KNOWLEDGE GRAPH REORGANIZATION VERIFICATION REPORT\n")
            f.write("="*70 + "\n\n")
            
            f.write(f"Original triples: {len(self.original_triples)}\n")
            f.write(f"Reorganized triples: {len(self.reorganized_triples)}\n")
            f.write(f"Mappings: {len(self.mapping)}\n\n")
            
            if self.info:
                f.write("PASSED CHECKS:\n")
                f.write("-"*70 + "\n")
                for info in self.info:
                    f.write(f"{info}\n")
                f.write("\n")
            
            if self.warnings:
                f.write("WARNINGS:\n")
                f.write("-"*70 + "\n")
                for warning in self.warnings:
                    f.write(f"{warning}\n")
                f.write("\n")
            
            if self.errors:
                f.write("ERRORS:\n")
                f.write("-"*70 + "\n")
                for error in self.errors:
                    f.write(f"{error}\n")
                f.write("\n")


def main():
    parser = argparse.ArgumentParser(
        description='Verify consistency of reorganized knowledge graph',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic verification
  python kg_verifier.py original.txt reorganized.txt
  
  # With mapping file
  python kg_verifier.py original.txt reorganized.txt --mapping reorganization_mapping.txt
  
  # Save report
  python kg_verifier.py original.txt reorganized.txt --report verification_report.txt
        """
    )
    
    parser.add_argument('original_file', help='Original knowledge graph file')
    parser.add_argument('reorganized_file', help='Reorganized knowledge graph file')
    parser.add_argument('--mapping', help='Mapping file (optional)')
    parser.add_argument('--report', help='Output report file (optional)')
    
    args = parser.parse_args()
    
    # Run verification
    verifier = KnowledgeGraphVerifier()
    success = verifier.run_all_verifications(
        args.original_file,
        args.reorganized_file,
        args.mapping
    )
    
    # Save report if requested
    if args.report:
        verifier.save_report(args.report)
        print(f"\nVerification report saved to: {args.report}")
    
    # Exit with appropriate code
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
