import random
import string
import argparse
import re
from typing import Dict, List, Tuple, Set, Optional
from pathlib import Path
from enum import Enum
from dataclasses import dataclass


class StringGenerationStrategy(Enum):
    """Strategies for generating random strings"""
    READABLE = "readable"  # consonant-vowel pattern
    RANDOM_ALPHA = "random_alpha"  # pure random letters
    ALPHANUMERIC = "alphanumeric"  # letters + numbers
    PRONOUNCEABLE = "pronounceable"  # more complex phonetic patterns
    MIXED_CASE = "mixed_case"  # random case mixing
    WORD_LIKE = "word_like"  # realistic word structure


@dataclass
class ObfuscationConfig:
    """Configuration for obfuscation parameters"""
    # Length parameters
    min_length: int = 5
    max_length: int = 12
    length_distribution: str = "uniform"  # uniform, normal, weighted
    
    # Generation strategy
    strategy: StringGenerationStrategy = StringGenerationStrategy.READABLE
    strategy_weights: Optional[Dict[StringGenerationStrategy, float]] = None
    
    # Number handling
    obfuscate_numbers: bool = True
    number_range_min: int = 1900
    number_range_max: int = 2100
    preserve_number_magnitude: bool = True  # Keep similar magnitude
    
    # What to obfuscate
    obfuscate_subjects: bool = True
    obfuscate_objects: bool = True
    obfuscate_relationships: bool = False
    
    # Advanced options
    preserve_case: bool = False
    add_hyphens: bool = False
    hyphen_probability: float = 0.2
    capitalize_first: bool = True
    preserve_special_chars: bool = False
    
    # Multi-word handling
    multi_word_strategy: str = "combined"  # combined, separate, preserve
    
    # Seed for reproducibility
    seed: Optional[int] = None


class AdvancedStringGenerator:
    """Advanced random string generator with multiple strategies"""
    
    def __init__(self, config: ObfuscationConfig):
        self.config = config
        if config.seed is not None:
            random.seed(config.seed)
    
    def generate(self, strategy: Optional[StringGenerationStrategy] = None) -> str:
        """Generate a random string based on strategy"""
        if strategy is None:
            strategy = self._select_strategy()
        
        length = self._get_length()
        
        generators = {
            StringGenerationStrategy.READABLE: self._generate_readable,
            StringGenerationStrategy.RANDOM_ALPHA: self._generate_random_alpha,
            StringGenerationStrategy.ALPHANUMERIC: self._generate_alphanumeric,
            StringGenerationStrategy.PRONOUNCEABLE: self._generate_pronounceable,
            StringGenerationStrategy.MIXED_CASE: self._generate_mixed_case,
            StringGenerationStrategy.WORD_LIKE: self._generate_word_like,
        }
        
        result = generators[strategy](length)
        
        # Apply post-processing
        result = self._apply_post_processing(result)
        
        return result
    
    def _select_strategy(self) -> StringGenerationStrategy:
        """Select strategy based on weights or use default"""
        if self.config.strategy_weights:
            strategies = list(self.config.strategy_weights.keys())
            weights = list(self.config.strategy_weights.values())
            return random.choices(strategies, weights=weights, k=1)[0]
        return self.config.strategy
    
    def _get_length(self) -> int:
        """Get length based on distribution"""
        if self.config.length_distribution == "uniform":
            return random.randint(self.config.min_length, self.config.max_length)
        elif self.config.length_distribution == "normal":
            mean = (self.config.min_length + self.config.max_length) / 2
            std = (self.config.max_length - self.config.min_length) / 4
            length = int(random.gauss(mean, std))
            return max(self.config.min_length, min(self.config.max_length, length))
        elif self.config.length_distribution == "weighted":
            # Favor medium lengths
            weights = []
            for i in range(self.config.min_length, self.config.max_length + 1):
                mid = (self.config.min_length + self.config.max_length) / 2
                weight = 1.0 - abs(i - mid) / (self.config.max_length - self.config.min_length)
                weights.append(weight)
            return random.choices(
                range(self.config.min_length, self.config.max_length + 1),
                weights=weights,
                k=1
            )[0]
        return self.config.min_length
    
    def _generate_readable(self, length: int) -> str:
        """Generate readable consonant-vowel pattern"""
        vowels = 'aeiou'
        consonants = 'bcdfghjklmnpqrstvwxyz'
        word = ''
        for i in range(length):
            if i % 2 == 0:
                word += random.choice(consonants)
            else:
                word += random.choice(vowels)
        return word
    
    def _generate_random_alpha(self, length: int) -> str:
        """Generate pure random alphabetic string"""
        return ''.join(random.choices(string.ascii_lowercase, k=length))
    
    def _generate_alphanumeric(self, length: int) -> str:
        """Generate alphanumeric string"""
        chars = string.ascii_lowercase + string.digits
        return ''.join(random.choices(chars, k=length))
    
    def _generate_pronounceable(self, length: int) -> str:
        """Generate more complex pronounceable patterns"""
        vowels = 'aeiou'
        consonants = 'bcdfghjklmnpqrstvwxyz'
        clusters = ['th', 'ch', 'sh', 'st', 'br', 'tr', 'pl', 'bl', 'cr', 'dr']
        
        word = ''
        i = 0
        while i < length:
            if i == 0 or (len(word) > 0 and word[-1] in vowels):
                # Start with consonant or after vowel
                if random.random() < 0.3 and i < length - 2:
                    cluster = random.choice(clusters)
                    word += cluster
                    i += len(cluster)
                else:
                    word += random.choice(consonants)
                    i += 1
            else:
                word += random.choice(vowels)
                i += 1
        
        return word[:length]
    
    def _generate_mixed_case(self, length: int) -> str:
        """Generate string with random case mixing"""
        word = self._generate_readable(length)
        return ''.join(c.upper() if random.random() < 0.3 else c for c in word)
    
    def _generate_word_like(self, length: int) -> str:
        """Generate realistic word-like structure"""
        # Start with pronounceable base
        word = self._generate_pronounceable(length)
        
        # Add common suffixes occasionally
        suffixes = ['er', 'ing', 'ed', 'ly', 'tion', 'ness']
        if random.random() < 0.3 and length > 5:
            suffix = random.choice(suffixes)
            word = word[:-len(suffix)] + suffix
        
        return word
    
    def _apply_post_processing(self, word: str) -> str:
        """Apply post-processing options"""
        # Capitalize first letter
        if self.config.capitalize_first:
            word = word.capitalize()
        
        # Add hyphens
        if self.config.add_hyphens and len(word) > 5 and random.random() < self.config.hyphen_probability:
            pos = random.randint(2, len(word) - 3)
            word = word[:pos] + '-' + word[pos:]
        
        return word


class KnowledgeGraphObfuscator:
    """Main obfuscator class"""
    
    def __init__(self, config: ObfuscationConfig):
        self.config = config
        self.generator = AdvancedStringGenerator(config)
        self.mappings: Dict[str, str] = {}
        self.used_replacements: Set[str] = set()
        
    def parse_knowledge_graph(self, file_path: str) -> List[Tuple[str, str, str]]:
        """Parse the knowledge graph file"""
        triples = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                parts = line.split('|')
                if len(parts) != 3:
                    print(f"Warning: Line {line_num} has incorrect format: {line}")
                    continue
                
                triples.append((parts[0].strip(), parts[1].strip(), parts[2].strip()))
        
        return triples
    
    def _is_number(self, text: str) -> bool:
        """Check if text is a number"""
        try:
            float(text)
            return True
        except ValueError:
            return False
    
    def _obfuscate_number(self, number_str: str) -> str:
        """Obfuscate a number while potentially preserving magnitude"""
        try:
            original_num = float(number_str)
            is_int = '.' not in number_str
            
            if self.config.preserve_number_magnitude:
                # Keep similar magnitude
                magnitude = len(str(int(abs(original_num))))
                min_val = 10 ** (magnitude - 1)
                max_val = 10 ** magnitude - 1
                new_num = random.randint(int(min_val), int(max_val))
            else:
                new_num = random.randint(
                    self.config.number_range_min,
                    self.config.number_range_max
                )
            
            return str(new_num) if is_int else str(float(new_num))
        except:
            return number_str
    
    def _generate_unique_replacement(self, original: str) -> str:
        """Generate a unique replacement that hasn't been used"""
        # Check if it's a number
        if self.config.obfuscate_numbers and self._is_number(original):
            return self._obfuscate_number(original)
        
        # Generate unique string
        max_attempts = 1000
        for _ in range(max_attempts):
            replacement = self.generator.generate()
            if replacement not in self.used_replacements:
                self.used_replacements.add(replacement)
                return replacement
        
        # Fallback: add random suffix
        replacement = self.generator.generate()
        suffix = ''.join(random.choices(string.ascii_lowercase, k=3))
        return replacement + suffix
    
    def _handle_multi_word(self, text: str) -> str:
        """Handle multi-word strings based on strategy"""
        # Check if this is a multi-word string
        if ' ' not in text and '-' not in text:
            return text
        
        if self.config.multi_word_strategy == "preserve":
            return text
        
        # Split on spaces and hyphens
        separators = []
        parts = []
        current = ""
        
        for char in text:
            if char in [' ', '-']:
                if current:
                    parts.append(current)
                    current = ""
                separators.append(char)
            else:
                current += char
        if current:
            parts.append(current)
        
        if self.config.multi_word_strategy == "combined":
            # Treat as single entity
            if text not in self.mappings:
                self.mappings[text] = self._generate_unique_replacement(text)
            return self.mappings[text]
        
        elif self.config.multi_word_strategy == "separate":
            # Obfuscate each part separately
            obfuscated_parts = []
            for part in parts:
                if part not in self.mappings:
                    self.mappings[part] = self._generate_unique_replacement(part)
                obfuscated_parts.append(self.mappings[part])
            
            # Reconstruct with original separators
            result = ""
            for i, part in enumerate(obfuscated_parts):
                result += part
                if i < len(separators):
                    result += separators[i]
            return result
        
        return text
    
    def _obfuscate_entity(self, entity: str) -> str:
        """Obfuscate a single entity (subject or object)"""
        # Handle multi-word entities
        if ' ' in entity or '-' in entity:
            return self._handle_multi_word(entity)
        
        # Single word entity
        if entity not in self.mappings:
            self.mappings[entity] = self._generate_unique_replacement(entity)
        
        return self.mappings[entity]
    
    def obfuscate_triples(self, triples: List[Tuple[str, str, str]]) -> List[Tuple[str, str, str]]:
        """Obfuscate the knowledge graph triples"""
        obfuscated = []
        
        for subject, relationship, obj in triples:
            # Obfuscate subject
            new_subject = subject
            if self.config.obfuscate_subjects:
                new_subject = self._obfuscate_entity(subject)
            
            # Obfuscate relationship
            new_relationship = relationship
            if self.config.obfuscate_relationships:
                new_relationship = self._obfuscate_entity(relationship)
            
            # Obfuscate object
            new_obj = obj
            if self.config.obfuscate_objects:
                new_obj = self._obfuscate_entity(obj)
            
            obfuscated.append((new_subject, new_relationship, new_obj))
        
        return obfuscated
    
    def save_knowledge_graph(self, triples: List[Tuple[str, str, str]], file_path: str):
        """Save obfuscated knowledge graph"""
        with open(file_path, 'w', encoding='utf-8') as f:
            for subject, relationship, obj in triples:
                f.write(f"{subject}|{relationship}|{obj}\n")
    
    def save_mapping(self, file_path: str, reverse: bool = False):
        """Save the mapping to a file"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("Original|Replacement\n")
            items = sorted(self.mappings.items())
            if reverse:
                items = [(v, k) for k, v in items]
            for original, replacement in items:
                f.write(f"{original}|{replacement}\n")
    
    def get_statistics(self) -> Dict:
        """Get obfuscation statistics"""
        return {
            'total_mappings': len(self.mappings),
            'unique_replacements': len(self.used_replacements),
            'number_mappings': sum(1 for k in self.mappings.keys() if self._is_number(k)),
            'multi_word_mappings': sum(1 for k in self.mappings.keys() if ' ' in k or '-' in k)
        }


def create_config_from_args(args) -> ObfuscationConfig:
    """Create configuration from command-line arguments"""
    config = ObfuscationConfig()
    
    # Length parameters
    config.min_length = args.min_length
    config.max_length = args.max_length
    config.length_distribution = args.length_distribution
    
    # Strategy
    config.strategy = StringGenerationStrategy(args.strategy)
    
    # Strategy weights
    if args.strategy_weights:
        weights_dict = {}
        for item in args.strategy_weights.split(','):
            strategy_name, weight = item.split(':')
            weights_dict[StringGenerationStrategy(strategy_name)] = float(weight)
        config.strategy_weights = weights_dict
    
    # Number handling
    config.obfuscate_numbers = args.obfuscate_numbers
    config.number_range_min = args.number_range_min
    config.number_range_max = args.number_range_max
    config.preserve_number_magnitude = args.preserve_number_magnitude
    
    # What to obfuscate
    config.obfuscate_subjects = args.obfuscate_subjects
    config.obfuscate_objects = args.obfuscate_objects
    config.obfuscate_relationships = args.obfuscate_relationships
    
    # Advanced options
    config.preserve_case = args.preserve_case
    config.add_hyphens = args.add_hyphens
    config.hyphen_probability = args.hyphen_probability
    config.capitalize_first = args.capitalize_first
    
    # Multi-word handling
    config.multi_word_strategy = args.multi_word_strategy
    
    # Seed
    config.seed = args.seed
    
    return config


def main():
    parser = argparse.ArgumentParser(
        description='Advanced Knowledge Graph Obfuscator with sophisticated options',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic obfuscation
  python kg_obfuscator_advanced.py input.txt output.txt
  
  # Custom length range with normal distribution
  python kg_obfuscator_advanced.py input.txt output.txt --min-length 4 --max-length 15 --length-distribution normal
  
  # Use pronounceable strategy
  python kg_obfuscator_advanced.py input.txt output.txt --strategy pronounceable
  
  # Mixed strategies with weights
  python kg_obfuscator_advanced.py input.txt output.txt --strategy-weights "readable:0.5,pronounceable:0.3,word_like:0.2"
  
  # Obfuscate everything including relationships
  python kg_obfuscator_advanced.py input.txt output.txt --obfuscate-relationships
  
  # Separate multi-word entities
  python kg_obfuscator_advanced.py input.txt output.txt --multi-word-strategy separate
  
  # Preserve number magnitude
  python kg_obfuscator_advanced.py input.txt output.txt --preserve-number-magnitude
        """
    )
    
    # Required arguments
    parser.add_argument('input_file', help='Input knowledge graph file')
    parser.add_argument('output_file', help='Output obfuscated knowledge graph file')
    
    # Output options
    parser.add_argument('--mapping-file', default='mapping.txt',
                       help='File to save the mapping (default: mapping.txt)')
    parser.add_argument('--reverse-mapping', action='store_true',
                       help='Save reverse mapping (obfuscated -> original)')
    
    # Length parameters
    parser.add_argument('--min-length', type=int, default=5,
                       help='Minimum length of generated strings (default: 5)')
    parser.add_argument('--max-length', type=int, default=12,
                       help='Maximum length of generated strings (default: 12)')
    parser.add_argument('--length-distribution', choices=['uniform', 'normal', 'weighted'],
                       default='uniform',
                       help='Distribution for string lengths (default: uniform)')
    
    # Generation strategy
    parser.add_argument('--strategy', 
                       choices=['readable', 'random_alpha', 'alphanumeric', 
                               'pronounceable', 'mixed_case', 'word_like'],
                       default='readable',
                       help='String generation strategy (default: readable)')
    parser.add_argument('--strategy-weights',
                       help='Comma-separated strategy:weight pairs for mixed strategies '
                            '(e.g., "readable:0.5,pronounceable:0.3,word_like:0.2")')
    
    # Number handling
    parser.add_argument('--obfuscate-numbers', action='store_true', default=True,
                       help='Obfuscate numbers (default: True)')
    parser.add_argument('--no-obfuscate-numbers', dest='obfuscate_numbers', 
                       action='store_false',
                       help='Do not obfuscate numbers')
    parser.add_argument('--number-range-min', type=int, default=1900,
                       help='Minimum value for random numbers (default: 1900)')
    parser.add_argument('--number-range-max', type=int, default=2100,
                       help='Maximum value for random numbers (default: 2100)')
    parser.add_argument('--preserve-number-magnitude', action='store_true', default=True,
                       help='Preserve magnitude of numbers (default: True)')
    parser.add_argument('--no-preserve-number-magnitude', dest='preserve_number_magnitude',
                       action='store_false',
                       help='Do not preserve number magnitude')
    
    # What to obfuscate
    parser.add_argument('--obfuscate-subjects', action='store_true', default=True,
                       help='Obfuscate subjects (default: True)')
    parser.add_argument('--no-obfuscate-subjects', dest='obfuscate_subjects',
                       action='store_false',
                       help='Do not obfuscate subjects')
    parser.add_argument('--obfuscate-objects', action='store_true', default=True,
                       help='Obfuscate objects (default: True)')
    parser.add_argument('--no-obfuscate-objects', dest='obfuscate_objects',
                       action='store_false',
                       help='Do not obfuscate objects')
    parser.add_argument('--obfuscate-relationships', action='store_true', default=False,
                       help='Obfuscate relationships (default: False)')
    
    # Advanced options
    parser.add_argument('--preserve-case', action='store_true',
                       help='Preserve original case patterns')
    parser.add_argument('--add-hyphens', action='store_true',
                       help='Randomly add hyphens to generated strings')
    parser.add_argument('--hyphen-probability', type=float, default=0.2,
                       help='Probability of adding hyphens (default: 0.2)')
    parser.add_argument('--capitalize-first', action='store_true', default=True,
                       help='Capitalize first letter (default: True)')
    parser.add_argument('--no-capitalize-first', dest='capitalize_first',
                       action='store_false',
                       help='Do not capitalize first letter')
    
    # Multi-word handling
    parser.add_argument('--multi-word-strategy', 
                       choices=['combined', 'separate', 'preserve'],
                       default='combined',
                       help='Strategy for multi-word entities (default: combined)')
    
    # Seed
    parser.add_argument('--seed', type=int, default=None,
                       help='Random seed for reproducibility (default: None)')
    
    # Verbosity
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    # Create configuration
    config = create_config_from_args(args)
    
    # Initialize obfuscator
    obfuscator = KnowledgeGraphObfuscator(config)
    
    # Parse input
    if args.verbose:
        print(f"Reading knowledge graph from: {args.input_file}")
    triples = obfuscator.parse_knowledge_graph(args.input_file)
    if args.verbose:
        print(f"Loaded {len(triples)} triples")
    
    # Obfuscate
    if args.verbose:
        print("Obfuscating knowledge graph...")
    obfuscated_triples = obfuscator.obfuscate_triples(triples)
    
    # Save results
    if args.verbose:
        print(f"Saving obfuscated graph to: {args.output_file}")
    obfuscator.save_knowledge_graph(obfuscated_triples, args.output_file)
    
    if args.verbose:
        print(f"Saving mapping to: {args.mapping_file}")
    obfuscator.save_mapping(args.mapping_file, reverse=args.reverse_mapping)
    
    # Print statistics
    stats = obfuscator.get_statistics()
    print("\n" + "="*60)
    print("OBFUSCATION COMPLETE")
    print("="*60)
    print(f"Total triples:           {len(obfuscated_triples)}")
    print(f"Total mappings:          {stats['total_mappings']}")
    print(f"Number mappings:         {stats['number_mappings']}")
    print(f"Multi-word mappings:     {stats['multi_word_mappings']}")
    print(f"Unique replacements:     {stats['unique_replacements']}")
    print("="*60)
    
    if args.verbose:
        print("\nConfiguration used:")
        print(f"  Strategy: {config.strategy.value}")
        print(f"  Length range: {config.min_length}-{config.max_length}")
        print(f"  Multi-word strategy: {config.multi_word_strategy}")
        print(f"  Obfuscate subjects: {config.obfuscate_subjects}")
        print(f"  Obfuscate objects: {config.obfuscate_objects}")
        print(f"  Obfuscate relationships: {config.obfuscate_relationships}")


if __name__ == "__main__":
    main()