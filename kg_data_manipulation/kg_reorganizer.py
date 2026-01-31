import random
import argparse
import re
from typing import Dict, List, Tuple, Set, Optional
from pathlib import Path
from enum import Enum
from dataclasses import dataclass
from collections import defaultdict


class EntityType(Enum):
    """Types of entities for consistent swapping"""
    NUMBER = "number"
    YEAR = "year"
    PERSON_NAME = "person_name"
    TITLE = "title"
    TAG = "tag"
    GENRE = "genre"
    LANGUAGE = "language"
    UNKNOWN = "unknown"


@dataclass
class ReorganizationConfig:
    """Configuration for reorganization"""
    # Type detection
    preserve_types: bool = True
    year_min: int = 1800
    year_max: int = 2100
    
    # Swapping strategy
    swap_subjects: bool = True
    swap_objects: bool = True
    swap_relationships: bool = False
    
    # Type-specific swapping
    swap_numbers_only_with_numbers: bool = True
    swap_years_only_with_years: bool = True
    swap_names_only_with_names: bool = True
    swap_titles_only_with_titles: bool = True
    
    # Multi-word handling
    detect_multi_word_titles: bool = True
    detect_person_names: bool = True
    
    # Randomization
    seed: Optional[int] = None
    shuffle_percentage: float = 1.0  # Percentage of entities to shuffle


class EntityTypeDetector:
    """Detect entity types for consistent swapping"""
    
    def __init__(self, config: ReorganizationConfig):
        self.config = config
        
        # Enhanced name patterns
        self.name_indicators = {
            'first_names': {
                'adrian', 'michael', 'bette', 'warren', 'jeff', 'clark', 
                'gerald', 'kiefer', 'eva', 'claudie', 'anastasia', 'john',
                'jane', 'david', 'sarah', 'robert', 'mary', 'james', 'linda',
                'william', 'patricia', 'richard', 'barbara', 'thomas', 'elizabeth',
                'charles', 'jennifer', 'joseph', 'maria', 'christopher', 'susan',
                'daniel', 'margaret', 'paul', 'dorothy', 'mark', 'lisa',
                'donald', 'nancy', 'george', 'karen', 'kenneth', 'betty',
                'steven', 'helen', 'edward', 'sandra', 'brian', 'donna',
                'ronald', 'carol', 'anthony', 'ruth', 'kevin', 'sharon',
                'jason', 'michelle', 'matthew', 'laura', 'gary', 'sarah',
                'timothy', 'kimberly', 'jose', 'deborah', 'larry', 'jessica',
                'jeffrey', 'shirley', 'frank', 'cynthia', 'scott', 'angela'
            },
            'title_words': {
                'the', 'a', 'an', 'of', 'and', 'in', 'to', 'for', 'at',
                'le', 'la', 'les', 'un', 'une', 'der', 'die', 'das', 'el'
            },
            'name_suffixes': {
                'jr', 'sr', 'ii', 'iii', 'iv', 'phd', 'md', 'esq'
            }
        }
        
        # Extended genre/tag patterns
        self.common_genres = {
            'drama', 'comedy', 'action', 'thriller', 'romance', 
            'horror', 'sci-fi', 'science fiction', 'documentary', 'animation',
            'adventure', 'fantasy', 'mystery', 'crime', 'war',
            'western', 'musical', 'biography', 'history', 'sport',
            'family', 'noir', 'superhero', 'zombie', 'vampire'
        }
        
        self.common_languages = {
            'english', 'french', 'spanish', 'german', 'italian', 
            'japanese', 'chinese', 'korean', 'russian', 'portuguese',
            'arabic', 'hindi', 'dutch', 'swedish', 'polish',
            'turkish', 'greek', 'hebrew', 'thai', 'vietnamese'
        }
        
        # Title indicators
        self.title_indicators = {
            'movie', 'film', 'show', 'series', 'episode', 'season',
            'part', 'chapter', 'volume', 'story', 'tale', 'saga'
        }
        
        # Common name patterns (for multi-word names)
        self.name_patterns = {
            'middle_initials': set('ABCDEFGHIJKLMNOPQRSTUVWXYZ'),
            'common_particles': {'de', 'von', 'van', 'del', 'da', 'di', 'mac', 'mc', 'o'}
        }
    
    def is_number(self, text: str) -> bool:
        """Check if text is a number"""
        try:
            float(text)
            return True
        except ValueError:
            return False
    
    def is_year(self, text: str) -> bool:
        """Check if text is a year"""
        if not self.is_number(text):
            return False
        try:
            num = int(float(text))
            return self.config.year_min <= num <= self.config.year_max
        except:
            return False
    
    def is_person_name(self, text: str, context: Optional[str] = None) -> bool:
        """Enhanced detection for person names"""
        if not self.config.detect_person_names:
            return False
        
        # Context helps a lot
        if context:
            context_lower = context.lower()
            # If used in a person-related relationship, likely a name
            if any(rel in context_lower for rel in ['director', 'writer', 'actor', 'actress', 'star', 'author', 'creator']):
                # Single word capitalized could be last name
                if text and text[0].isupper() and ' ' not in text:
                    return True
        
        words = text.split()
        
        # Single word checks
        if len(words) == 1:
            word = words[0]
            # Check if it's a known first name (capitalized)
            if word and word[0].isupper():
                if word.lower() in self.name_indicators['first_names']:
                    return True
            return False
        
        # Multi-word checks (2-4 words is typical for names)
        if 2 <= len(words) <= 4:
            # All words should start with capital (except particles)
            for i, word in enumerate(words):
                if not word:
                    continue
                    
                word_lower = word.lower()
                
                # Particles can be lowercase
                if word_lower in self.name_patterns['common_particles']:
                    continue
                
                # Middle initials (single capital letter, possibly with period)
                if len(word.rstrip('.')) == 1 and word[0].isupper():
                    continue
                
                # Suffixes can be mixed case
                if word_lower in self.name_indicators['name_suffixes']:
                    continue
                
                # Regular word should start with capital
                if not word[0].isupper():
                    return False
            
            # Check first word is a known first name or follows name pattern
            first_word = words[0].lower()
            if first_word in self.name_indicators['first_names']:
                return True
            
            # If we have exactly 2 capitalized words, likely a name (First Last)
            capitalized_words = [w for w in words if w and w[0].isupper() and len(w) > 1]
            if len(capitalized_words) == 2:
                return True
            
            # If we have 3 words with middle initial pattern (First M. Last)
            if len(words) == 3 and len(words[1].rstrip('.')) == 1 and words[1][0].isupper():
                return True
        
        return False
    
    def is_title(self, text: str, context: Optional[str] = None) -> bool:
        """Enhanced detection for titles (movies, books, etc.)"""
        if not self.config.detect_multi_word_titles:
            return False
        
        # Context is very helpful for titles
        if context:
            context_lower = context.lower()
            # If it's a subject with movie/book relationships, likely a title
            if any(rel in context_lower for rel in ['directed_by', 'written_by', 'starred', 'genre', 'tags', 'release']):
                # Even single capitalized words can be titles in this context
                if text and text[0].isupper():
                    return True
        
        words = text.split()
        
        # Single word check
        if len(words) == 1:
            word = words[0]
            # Single capitalized word could be a title
            if word and word[0].isupper():
                # Check if it contains title indicators
                if any(indicator in word.lower() for indicator in self.title_indicators):
                    return True
                # In context of being a subject, single cap word might be a title
                # But we need more evidence, so return False here
                return False
        
        # Multi-word checks
        if len(words) >= 2:
            # Check for common title patterns
            first_word_lower = words[0].lower()
            
            # Starts with articles (The, A, An, etc.)
            if first_word_lower in self.name_indicators['title_words']:
                # Make sure it's not likely a person name
                if not self.is_person_name(text, context):
                    return True
            
            # Contains title indicator words
            if any(indicator in text.lower() for indicator in self.title_indicators):
                return True
            
            # Most words capitalized (title case)
            capitalized_count = sum(1 for w in words if w and w[0].isupper())
            if capitalized_count >= len(words) * 0.6:  # 60% or more capitalized
                # Not a person name
                if not self.is_person_name(text, context):
                    # Could be a title
                    return True
            
            # Check for colon pattern (Title: Subtitle)
            if ':' in text:
                return True
        
        return False
    
    def is_genre(self, text: str) -> bool:
        """Check if text is a genre"""
        return text.lower() in self.common_genres
    
    def is_language(self, text: str) -> bool:
        """Check if text is a language"""
        return text.lower() in self.common_languages
    
    def detect_type(self, text: str, context: Optional[str] = None) -> EntityType:
        """
        Enhanced entity type detection with context awareness
        
        Args:
            text: The entity text
            context: Optional context (like relationship name or usage pattern) to help detection
        
        Returns:
            EntityType
        """
        # Check in order of specificity
        
        # 1. Year (most specific number)
        if self.is_year(text):
            return EntityType.YEAR
        
        # 2. Generic number
        if self.is_number(text):
            return EntityType.NUMBER
        
        # 3. Language (specific category)
        if self.is_language(text):
            return EntityType.LANGUAGE
        
        # 4. Genre (specific category)
        if self.is_genre(text):
            return EntityType.GENRE
        
        # 5. Use context for classification (MOST IMPORTANT FOR TITLES AND NAMES)
        if context:
            context_lower = context.lower()
            
            # Check if it's a SUBJECT with movie/title relationships (HIGH PRIORITY FOR TITLES)
            if 'subject with relationships:' in context_lower:
                movie_rels = ['directed_by', 'written_by', 'starred_actors', 'has_genre', 
                             'has_tags', 'release_year', 'in_language']
                if any(rel in context_lower for rel in movie_rels):
                    # This is almost certainly a title
                    if self.is_title(text, context):
                        return EntityType.TITLE
                    # Even if is_title returns False, if it starts with article, it's a title
                    words = text.split()
                    if len(words) >= 2 and words[0].lower() in self.name_indicators['title_words']:
                        return EntityType.TITLE
            
            # Check for PERSON_NAME as object of person-related relationships
            person_rels = ['directed_by', 'written_by', 'starred_actors']
            if any(rel in context_lower for rel in person_rels):
                # Only if it's NOT in a subject context
                if 'subject with relationships:' not in context_lower:
                    if self.is_person_name(text, context):
                        return EntityType.PERSON_NAME
                    # If in person relationship but not detected, try harder
                    words = text.split()
                    if 1 <= len(words) <= 4:  # Reasonable name length
                        # Check for capitalization pattern
                        if all(w and w[0].isupper() for w in words if len(w) > 1):
                            return EntityType.PERSON_NAME
        
        # 6. Person name detection (without context or with weak context)
        if self.is_person_name(text, context):
            return EntityType.PERSON_NAME
        
        # 7. Title detection (without context or with weak context)
        if self.is_title(text, context):
            return EntityType.TITLE
        
        # 8. Tags (lowercase, short phrases)
        if text.islower() or (len(text.split()) <= 3 and '-' in text):
            return EntityType.TAG
        
        # 9. If nothing else matches, it's unknown
        return EntityType.UNKNOWN


class KnowledgeGraphReorganizer:
    """Main reorganizer class"""
    
    def __init__(self, config: ReorganizationConfig):
        self.config = config
        self.detector = EntityTypeDetector(config)
        
        if config.seed is not None:
            random.seed(config.seed)
        
        # Storage
        self.entity_to_type: Dict[str, EntityType] = {}
        self.type_to_entities: Dict[EntityType, Set[str]] = defaultdict(set)
        self.swap_mapping: Dict[str, str] = {}
        
        # Statistics
        self.stats = {
            'total_entities': 0,
            'swapped_entities': 0,
            'type_counts': defaultdict(int)
        }
    
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
    
    def analyze_entities(self, triples: List[Tuple[str, str, str]]):
        """Analyze and categorize all entities"""
        print("Analyzing entity types...")
        
        # Track entity usage to build better context
        entity_usage = defaultdict(lambda: {'as_subject': [], 'as_object': []})
        
        for subject, relationship, obj in triples:
            entity_usage[subject]['as_subject'].append(relationship)
            entity_usage[obj]['as_object'].append(relationship)
        
        for subject, relationship, obj in triples:
            # Analyze subject with context
            if self.config.swap_subjects and subject not in self.entity_to_type:
                # Subject context: being a subject + its relationships
                context = f"subject with relationships: {', '.join(entity_usage[subject]['as_subject'])}"
                entity_type = self.detector.detect_type(subject, context=context)
                self.entity_to_type[subject] = entity_type
                self.type_to_entities[entity_type].add(subject)
                self.stats['type_counts'][entity_type.value] += 1
            
            # Analyze object with context
            if self.config.swap_objects and obj not in self.entity_to_type:
                # Object context: the relationship it's used in
                context = relationship
                entity_type = self.detector.detect_type(obj, context=context)
                self.entity_to_type[obj] = entity_type
                self.type_to_entities[entity_type].add(obj)
                self.stats['type_counts'][entity_type.value] += 1
            
            # Analyze relationship if needed
            if self.config.swap_relationships and relationship not in self.entity_to_type:
                entity_type = EntityType.UNKNOWN
                self.entity_to_type[relationship] = entity_type
                self.type_to_entities[entity_type].add(relationship)
        
        self.stats['total_entities'] = len(self.entity_to_type)
    
    def _should_swap_types(self, type1: EntityType, type2: EntityType) -> bool:
        """Determine if two types can be swapped"""
        if not self.config.preserve_types:
            return True
        
        # Same type is always OK
        if type1 == type2:
            return True
        
        # Check specific constraints
        if self.config.swap_numbers_only_with_numbers:
            if type1 == EntityType.NUMBER or type2 == EntityType.NUMBER:
                return type1 == type2
        
        if self.config.swap_years_only_with_years:
            if type1 == EntityType.YEAR or type2 == EntityType.YEAR:
                return type1 == type2
        
        if self.config.swap_names_only_with_names:
            if type1 == EntityType.PERSON_NAME or type2 == EntityType.PERSON_NAME:
                return type1 == type2
        
        if self.config.swap_titles_only_with_titles:
            if type1 == EntityType.TITLE or type2 == EntityType.TITLE:
                return type1 == type2
        
        return True
    
    def create_swap_mapping(self):
        """Create consistent swap mapping for entities"""
        print("Creating swap mapping...")
        
        # Group entities by type for swapping
        if self.config.preserve_types:
            # Swap within each type
            for entity_type, entities in self.type_to_entities.items():
                # NEVER swap UNKNOWN entities - keep them unchanged
                if entity_type == EntityType.UNKNOWN:
                    print(f"Skipping {len(entities)} UNKNOWN entities (will not be swapped)")
                    continue
                
                entities_list = list(entities)
                
                # Determine how many to swap
                num_to_swap = int(len(entities_list) * self.config.shuffle_percentage)
                num_to_swap = max(2, min(num_to_swap, len(entities_list)))  # At least 2, at most all
                
                if len(entities_list) >= 2:
                    # Select random subset to swap
                    to_swap = random.sample(entities_list, num_to_swap)
                    
                    # Create shuffled version
                    shuffled = to_swap.copy()
                    random.shuffle(shuffled)
                    
                    # Ensure we actually swap (not identity)
                    while shuffled == to_swap and len(to_swap) > 1:
                        random.shuffle(shuffled)
                    
                    # Create mapping
                    for original, swapped in zip(to_swap, shuffled):
                        self.swap_mapping[original] = swapped
                        self.stats['swapped_entities'] += 1
        else:
            # Swap across all types (but still skip UNKNOWN)
            all_entities = [e for e in self.entity_to_type.keys() 
                          if self.entity_to_type[e] != EntityType.UNKNOWN]
            num_to_swap = int(len(all_entities) * self.config.shuffle_percentage)
            num_to_swap = max(2, min(num_to_swap, len(all_entities)))
            
            if len(all_entities) >= 2:
                to_swap = random.sample(all_entities, num_to_swap)
                shuffled = to_swap.copy()
                random.shuffle(shuffled)
                
                while shuffled == to_swap and len(to_swap) > 1:
                    random.shuffle(shuffled)
                
                for original, swapped in zip(to_swap, shuffled):
                    self.swap_mapping[original] = swapped
                    self.stats['swapped_entities'] += 1
        
        # Fill in identity mappings for non-swapped entities (including all UNKNOWN)
        for entity in self.entity_to_type.keys():
            if entity not in self.swap_mapping:
                self.swap_mapping[entity] = entity
    
    def reorganize_triples(self, triples: List[Tuple[str, str, str]]) -> List[Tuple[str, str, str]]:
        """Reorganize triples using swap mapping"""
        print("Reorganizing knowledge graph...")
        
        reorganized = []
        for subject, relationship, obj in triples:
            new_subject = self.swap_mapping.get(subject, subject)
            new_relationship = self.swap_mapping.get(relationship, relationship)
            new_obj = self.swap_mapping.get(obj, obj)
            
            reorganized.append((new_subject, new_relationship, new_obj))
        
        return reorganized
    
    def save_knowledge_graph(self, triples: List[Tuple[str, str, str]], file_path: str):
        """Save reorganized knowledge graph"""
        with open(file_path, 'w', encoding='utf-8') as f:
            for subject, relationship, obj in triples:
                f.write(f"{subject}|{relationship}|{obj}\n")
    
    def save_mapping(self, file_path: str):
        """Save the swap mapping"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("Original|Swapped_To|Type\n")
            
            # Only save entities that were actually swapped
            for original, swapped in sorted(self.swap_mapping.items()):
                if original != swapped:
                    entity_type = self.entity_to_type.get(original, EntityType.UNKNOWN)
                    f.write(f"{original}|{swapped}|{entity_type.value}\n")
    
    def save_full_mapping(self, file_path: str):
        """Save complete mapping including identity mappings"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("Original|Swapped_To|Type|Changed\n")
            
            for original, swapped in sorted(self.swap_mapping.items()):
                entity_type = self.entity_to_type.get(original, EntityType.UNKNOWN)
                changed = "Yes" if original != swapped else "No"
                f.write(f"{original}|{swapped}|{entity_type.value}|{changed}\n")
    
    def save_type_analysis(self, file_path: str):
        """Save detailed type analysis"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("Entity Type Analysis\n")
            f.write("="*60 + "\n\n")
            
            for entity_type in EntityType:
                entities = self.type_to_entities.get(entity_type, set())
                if entities:
                    f.write(f"\n{entity_type.value.upper()} ({len(entities)} entities):\n")
                    f.write("-" * 60 + "\n")
                    for entity in sorted(entities):
                        swapped = self.swap_mapping.get(entity, entity)
                        if entity != swapped:
                            f.write(f"  {entity} → {swapped}\n")
                        else:
                            f.write(f"  {entity} (unchanged)\n")
    
    def save_unknown_entities(self, file_path: str, triples: List[Tuple[str, str, str]]):
        """Save detailed list of unknown entities with context for improving parser"""
        unknown_entities = self.type_to_entities.get(EntityType.UNKNOWN, set())
        
        # Helper function for number checking
        def _is_number(text):
            try:
                float(text)
                return True
            except:
                return False
        
        if not unknown_entities:
            # Create empty file with message
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("Unknown Entities Analysis\n")
                f.write("="*80 + "\n\n")
                f.write("No unknown entities detected - all entities were successfully classified!\n")
            return
        
        # Build context information for each unknown entity
        entity_context = defaultdict(lambda: {
            'as_subject': [],
            'as_object': [],
            'relationships_when_subject': set(),
            'relationships_when_object': set(),
            'frequency': 0
        })
        
        for subject, relationship, obj in triples:
            if subject in unknown_entities:
                entity_context[subject]['as_subject'].append(f"{relationship}|{obj}")
                entity_context[subject]['relationships_when_subject'].add(relationship)
                entity_context[subject]['frequency'] += 1
            
            if obj in unknown_entities:
                entity_context[obj]['as_object'].append(f"{subject}|{relationship}")
                entity_context[obj]['relationships_when_object'].add(relationship)
                entity_context[obj]['frequency'] += 1
        
        # Write detailed analysis
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("Unknown Entities Analysis - For Parser Improvement\n")
            f.write("="*80 + "\n\n")
            f.write(f"Total unknown entities: {len(unknown_entities)}\n")
            f.write(f"These entities were not classified and remain UNCHANGED in reorganization.\n\n")
            f.write("Use this file to improve entity type detection rules.\n")
            f.write("="*80 + "\n\n")
            
            # Sort by frequency (most common first)
            sorted_entities = sorted(unknown_entities, 
                                   key=lambda x: entity_context[x]['frequency'], 
                                   reverse=True)
            
            for entity in sorted_entities:
                context = entity_context[entity]
                f.write(f"\nEntity: '{entity}'\n")
                f.write("-" * 80 + "\n")
                f.write(f"Frequency: {context['frequency']} occurrences\n")
                
                # Characteristics
                characteristics = []
                if ' ' in entity:
                    characteristics.append(f"Multi-word ({len(entity.split())} words)")
                if '-' in entity:
                    characteristics.append("Contains hyphen")
                if entity[0].isupper():
                    characteristics.append("Starts with capital")
                if entity.isupper():
                    characteristics.append("All uppercase")
                if entity.islower():
                    characteristics.append("All lowercase")
                if any(c.isdigit() for c in entity):
                    characteristics.append("Contains digits")
                
                if characteristics:
                    f.write(f"Characteristics: {', '.join(characteristics)}\n")
                
                # Usage as subject
                if context['as_subject']:
                    f.write(f"\nUsed as SUBJECT ({len(context['as_subject'])} times):\n")
                    f.write(f"  Relationships: {', '.join(sorted(context['relationships_when_subject']))}\n")
                    f.write(f"  Examples:\n")
                    for example in context['as_subject'][:3]:  # Show first 3
                        f.write(f"    {entity}|{example}\n")
                    if len(context['as_subject']) > 3:
                        f.write(f"    ... and {len(context['as_subject']) - 3} more\n")
                
                # Usage as object
                if context['as_object']:
                    f.write(f"\nUsed as OBJECT ({len(context['as_object'])} times):\n")
                    f.write(f"  Relationships: {', '.join(sorted(context['relationships_when_object']))}\n")
                    f.write(f"  Examples:\n")
                    for example in context['as_object'][:3]:  # Show first 3
                        f.write(f"    {example}|{entity}\n")
                    if len(context['as_object']) > 3:
                        f.write(f"    ... and {len(context['as_object']) - 3} more\n")
                
                # Suggestions for classification
                f.write(f"\nSuggested Classification Hints:\n")
                
                # Track all suggestions
                suggestions = []
                confidence_high = []
                confidence_medium = []
                confidence_low = []
                
                # Analyze based on usage as SUBJECT
                if context['relationships_when_subject']:
                    subject_rels = list(context['relationships_when_subject'])
                    
                    # High confidence TITLE indicators
                    title_rels = {'directed_by', 'written_by', 'starred_actors', 'has_genre', 
                                 'has_tags', 'release_year', 'in_language'}
                    if any(r in title_rels for r in subject_rels):
                        confidence_high.append("TITLE")
                        suggestions.append(("TITLE", "appears as subject with movie-related relationships", "HIGH"))
                    
                    # Medium confidence based on other patterns
                    elif any('has_' in r or 'in_' in r for r in subject_rels):
                        confidence_medium.append("TITLE")
                        suggestions.append(("TITLE", "has descriptive relationships as subject", "MEDIUM"))
                
                # Analyze based on usage as OBJECT
                if context['relationships_when_object']:
                    object_rels = list(context['relationships_when_object'])
                    
                    # High confidence PERSON_NAME indicators
                    person_rels = {'directed_by', 'written_by', 'starred_actors'}
                    matched_person_rels = [r for r in object_rels if r in person_rels]
                    
                    if matched_person_rels:
                        confidence_high.append("PERSON_NAME")
                        role = "director" if "directed_by" in matched_person_rels else \
                               "writer" if "written_by" in matched_person_rels else "actor"
                        suggestions.append(("PERSON_NAME", f"appears as {role}", "HIGH"))
                    
                    # High confidence GENRE indicator
                    if 'has_genre' in object_rels:
                        confidence_high.append("GENRE")
                        suggestions.append(("GENRE", "appears as genre value", "HIGH"))
                    
                    # Medium confidence TAG indicator
                    if 'has_tags' in object_rels:
                        confidence_medium.append("TAG")
                        suggestions.append(("TAG", "appears as tag value", "MEDIUM"))
                    
                    # Medium confidence LANGUAGE indicator
                    if 'in_language' in object_rels:
                        confidence_medium.append("LANGUAGE")
                        suggestions.append(("LANGUAGE", "appears as language value", "MEDIUM"))
                    
                    # YEAR indicator
                    if 'release_year' in object_rels:
                        if _is_number(entity):
                            confidence_high.append("YEAR")
                            suggestions.append(("YEAR", "appears as year (check year range detection)", "HIGH"))
                        else:
                            confidence_low.append("YEAR")
                            suggestions.append(("YEAR", "used as year but not numeric - data issue?", "LOW"))
                
                # Additional entity characteristics analysis
                char_suggestions = []
                
                # Multi-word capitalized = likely title or name
                if ' ' in entity:
                    words = entity.split()
                    caps_count = sum(1 for w in words if w and w[0].isupper())
                    
                    if caps_count == len(words):
                        # All capitalized
                        if len(words) == 2:
                            char_suggestions.append("Likely PERSON_NAME (2 capitalized words)")
                        elif len(words) >= 3:
                            char_suggestions.append("Could be PERSON_NAME or TITLE (multiple capitalized words)")
                    elif words[0][0].isupper() and words[0].lower() in ['the', 'a', 'an']:
                        char_suggestions.append("Likely TITLE (starts with article)")
                
                # All lowercase = likely tag
                if entity.islower():
                    char_suggestions.append("Likely TAG (all lowercase)")
                
                # Has hyphen = could be tag or rating
                if '-' in entity and not ' ' in entity:
                    char_suggestions.append("Could be TAG or custom type (contains hyphen)")
                
                # Write suggestions grouped by confidence
                if confidence_high:
                    f.write(f"  [HIGH CONFIDENCE]\n")
                    for stype, reason, conf in suggestions:
                        if conf == "HIGH":
                            f.write(f"    → {stype}: {reason}\n")
                
                if confidence_medium:
                    f.write(f"  [MEDIUM CONFIDENCE]\n")
                    for stype, reason, conf in suggestions:
                        if conf == "MEDIUM":
                            f.write(f"    → {stype}: {reason}\n")
                
                if confidence_low:
                    f.write(f"  [LOW CONFIDENCE]\n")
                    for stype, reason, conf in suggestions:
                        if conf == "LOW":
                            f.write(f"    → {stype}: {reason}\n")
                
                if char_suggestions:
                    f.write(f"  [BASED ON CHARACTERISTICS]\n")
                    for suggestion in char_suggestions:
                        f.write(f"    → {suggestion}\n")
                
                if not suggestions and not char_suggestions:
                    f.write(f"  → No clear classification (review context manually)\n")
                
                f.write("\n")
            
            # Summary statistics
            f.write("\n" + "="*80 + "\n")
            f.write("SUMMARY FOR PARSER IMPROVEMENT\n")
            f.write("="*80 + "\n\n")
            
            # Group by likely type based on context
            likely_titles = []
            likely_names = []
            likely_tags = []
            likely_other = []
            
            for entity in unknown_entities:
                context = entity_context[entity]
                rels_as_subject = context['relationships_when_subject']
                rels_as_object = context['relationships_when_object']
                
                if any(r in ['directed_by', 'written_by', 'starred_actors', 'has_genre', 'has_tags'] for r in rels_as_subject):
                    likely_titles.append(entity)
                elif any(r in ['directed_by', 'written_by', 'starred_actors'] for r in rels_as_object):
                    likely_names.append(entity)
                elif 'has_tags' in rels_as_object:
                    likely_tags.append(entity)
                else:
                    likely_other.append(entity)
            
            if likely_titles:
                f.write(f"\nLikely TITLES ({len(likely_titles)}):\n")
                for entity in sorted(likely_titles)[:10]:
                    f.write(f"  - {entity}\n")
                if len(likely_titles) > 10:
                    f.write(f"  ... and {len(likely_titles) - 10} more\n")
            
            if likely_names:
                f.write(f"\nLikely PERSON_NAMES ({len(likely_names)}):\n")
                for entity in sorted(likely_names)[:10]:
                    f.write(f"  - {entity}\n")
                if len(likely_names) > 10:
                    f.write(f"  ... and {len(likely_names) - 10} more\n")
            
            if likely_tags:
                f.write(f"\nLikely TAGS ({len(likely_tags)}):\n")
                for entity in sorted(likely_tags)[:10]:
                    f.write(f"  - {entity}\n")
                if len(likely_tags) > 10:
                    f.write(f"  ... and {len(likely_tags) - 10} more\n")
            
            if likely_other:
                f.write(f"\nUNCLEAR ({len(likely_other)}):\n")
                for entity in sorted(likely_other)[:10]:
                    f.write(f"  - {entity}\n")
                if len(likely_other) > 10:
                    f.write(f"  ... and {len(likely_other) - 10} more\n")
            
            f.write("\n" + "="*80 + "\n")
            f.write("RECOMMENDATIONS:\n")
            f.write("="*80 + "\n\n")
            f.write("1. Review entities listed as 'Likely TITLES' and update title detection rules\n")
            f.write("2. Review entities listed as 'Likely PERSON_NAMES' and update name detection\n")
            f.write("3. Add specific entity names to detection dictionaries if needed\n")
            f.write("4. Consider relationship context for better classification\n")
            f.write("5. Check for patterns in multi-word entities\n\n")
    
    def get_statistics(self) -> Dict:
        """Get reorganization statistics"""
        return {
            'total_entities': self.stats['total_entities'],
            'swapped_entities': self.stats['swapped_entities'],
            'unchanged_entities': self.stats['total_entities'] - self.stats['swapped_entities'],
            'type_counts': dict(self.stats['type_counts']),
            'swap_percentage': (self.stats['swapped_entities'] / max(1, self.stats['total_entities'])) * 100
        }


def create_config_from_args(args) -> ReorganizationConfig:
    """Create configuration from command-line arguments"""
    config = ReorganizationConfig()
    
    # Type preservation
    config.preserve_types = args.preserve_types
    config.year_min = args.year_min
    config.year_max = args.year_max
    
    # What to swap
    config.swap_subjects = args.swap_subjects
    config.swap_objects = args.swap_objects
    config.swap_relationships = args.swap_relationships
    
    # Type-specific swapping
    config.swap_numbers_only_with_numbers = args.swap_numbers_only_with_numbers
    config.swap_years_only_with_years = args.swap_years_only_with_years
    config.swap_names_only_with_names = args.swap_names_only_with_names
    config.swap_titles_only_with_titles = args.swap_titles_only_with_titles
    
    # Detection
    config.detect_multi_word_titles = args.detect_multi_word_titles
    config.detect_person_names = args.detect_person_names
    
    # Randomization
    config.seed = args.seed
    config.shuffle_percentage = args.shuffle_percentage
    
    return config


def main():
    parser = argparse.ArgumentParser(
        description='Advanced Knowledge Graph Reorganizer - Shuffles entities while maintaining consistency',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic reorganization
  python kg_reorganizer.py input.txt output.txt
  
  # Swap only titles, keep everything else
  python kg_reorganizer.py input.txt output.txt --no-swap-objects
  
  # Swap everything including relationships
  python kg_reorganizer.py input.txt output.txt --swap-relationships
  
  # Partial shuffle (50% of entities)
  python kg_reorganizer.py input.txt output.txt --shuffle-percentage 0.5
  
  # Disable type preservation (swap anything with anything)
  python kg_reorganizer.py input.txt output.txt --no-preserve-types
  
  # Reproducible results
  python kg_reorganizer.py input.txt output.txt --seed 42
        """
    )
    
    # Required arguments
    parser.add_argument('input_file', help='Input knowledge graph file')
    parser.add_argument('output_file', help='Output reorganized knowledge graph file')
    
    # Output options
    parser.add_argument('--mapping-file', default='reorganization_mapping.txt',
                       help='File to save swap mapping (default: reorganization_mapping.txt)')
    parser.add_argument('--full-mapping-file', default='full_mapping.txt',
                       help='File to save complete mapping (default: full_mapping.txt)')
    parser.add_argument('--type-analysis-file', default='type_analysis.txt',
                       help='File to save type analysis (default: type_analysis.txt)')
    parser.add_argument('--unknown-entities-file', default='unknown_entities.txt',
                       help='File to save unknown entities analysis (default: unknown_entities.txt)')
    
    # Type preservation
    parser.add_argument('--preserve-types', action='store_true', default=True,
                       help='Preserve entity types when swapping (default: True)')
    parser.add_argument('--no-preserve-types', dest='preserve_types', action='store_false',
                       help='Allow swapping across different entity types')
    parser.add_argument('--year-min', type=int, default=1800,
                       help='Minimum year for year detection (default: 1800)')
    parser.add_argument('--year-max', type=int, default=2100,
                       help='Maximum year for year detection (default: 2100)')
    
    # What to swap
    parser.add_argument('--swap-subjects', action='store_true', default=True,
                       help='Swap subjects (default: True)')
    parser.add_argument('--no-swap-subjects', dest='swap_subjects', action='store_false',
                       help='Do not swap subjects')
    parser.add_argument('--swap-objects', action='store_true', default=True,
                       help='Swap objects (default: True)')
    parser.add_argument('--no-swap-objects', dest='swap_objects', action='store_false',
                       help='Do not swap objects')
    parser.add_argument('--swap-relationships', action='store_true', default=False,
                       help='Swap relationships (default: False)')
    
    # Type-specific swapping
    parser.add_argument('--swap-numbers-only-with-numbers', action='store_true', default=True,
                       help='Numbers only swap with numbers (default: True)')
    parser.add_argument('--no-swap-numbers-only-with-numbers', 
                       dest='swap_numbers_only_with_numbers', action='store_false',
                       help='Allow numbers to swap with non-numbers')
    parser.add_argument('--swap-years-only-with-years', action='store_true', default=True,
                       help='Years only swap with years (default: True)')
    parser.add_argument('--no-swap-years-only-with-years',
                       dest='swap_years_only_with_years', action='store_false',
                       help='Allow years to swap with non-years')
    parser.add_argument('--swap-names-only-with-names', action='store_true', default=True,
                       help='Names only swap with names (default: True)')
    parser.add_argument('--no-swap-names-only-with-names',
                       dest='swap_names_only_with_names', action='store_false',
                       help='Allow names to swap with non-names')
    parser.add_argument('--swap-titles-only-with-titles', action='store_true', default=True,
                       help='Titles only swap with titles (default: True)')
    parser.add_argument('--no-swap-titles-only-with-titles',
                       dest='swap_titles_only_with_titles', action='store_false',
                       help='Allow titles to swap with non-titles')
    
    # Detection options
    parser.add_argument('--detect-multi-word-titles', action='store_true', default=True,
                       help='Detect multi-word titles (default: True)')
    parser.add_argument('--no-detect-multi-word-titles',
                       dest='detect_multi_word_titles', action='store_false',
                       help='Do not detect multi-word titles')
    parser.add_argument('--detect-person-names', action='store_true', default=True,
                       help='Detect person names (default: True)')
    parser.add_argument('--no-detect-person-names',
                       dest='detect_person_names', action='store_false',
                       help='Do not detect person names')
    
    # Randomization
    parser.add_argument('--seed', type=int, default=None,
                       help='Random seed for reproducibility (default: None)')
    parser.add_argument('--shuffle-percentage', type=float, default=1.0,
                       help='Percentage of entities to shuffle (0.0-1.0, default: 1.0)')
    
    # Verbosity
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    parser.add_argument('--save-full-mapping', action='store_true',
                       help='Save complete mapping including unchanged entities')
    parser.add_argument('--save-type-analysis', action='store_true',
                       help='Save detailed type analysis')
    parser.add_argument('--save-unknown-entities', action='store_true', default=True,
                       help='Save unknown entities analysis for parser improvement (default: True)')
    parser.add_argument('--no-save-unknown-entities', dest='save_unknown_entities',
                       action='store_false',
                       help='Do not save unknown entities analysis')
    
    args = parser.parse_args()
    
    # Validate shuffle percentage
    if not 0.0 <= args.shuffle_percentage <= 1.0:
        parser.error("--shuffle-percentage must be between 0.0 and 1.0")
    
    # Create configuration
    config = create_config_from_args(args)
    
    # Initialize reorganizer
    reorganizer = KnowledgeGraphReorganizer(config)
    
    # Parse input
    if args.verbose:
        print(f"Reading knowledge graph from: {args.input_file}")
    triples = reorganizer.parse_knowledge_graph(args.input_file)
    if args.verbose:
        print(f"Loaded {len(triples)} triples")
    
    # Analyze entities
    reorganizer.analyze_entities(triples)
    
    # Create swap mapping
    reorganizer.create_swap_mapping()
    
    # Reorganize
    reorganized_triples = reorganizer.reorganize_triples(triples)
    
    # Save results
    if args.verbose:
        print(f"Saving reorganized graph to: {args.output_file}")
    reorganizer.save_knowledge_graph(reorganized_triples, args.output_file)
    
    if args.verbose:
        print(f"Saving mapping to: {args.mapping_file}")
    reorganizer.save_mapping(args.mapping_file)
    
    if args.save_full_mapping:
        if args.verbose:
            print(f"Saving full mapping to: {args.full_mapping_file}")
        reorganizer.save_full_mapping(args.full_mapping_file)
    
    if args.save_type_analysis:
        if args.verbose:
            print(f"Saving type analysis to: {args.type_analysis_file}")
        reorganizer.save_type_analysis(args.type_analysis_file)
    
    if args.save_unknown_entities:
        if args.verbose:
            print(f"Saving unknown entities analysis to: {args.unknown_entities_file}")
        reorganizer.save_unknown_entities(args.unknown_entities_file, triples)
    
    # Print statistics
    stats = reorganizer.get_statistics()
    print("\n" + "="*60)
    print("REORGANIZATION COMPLETE")
    print("="*60)
    print(f"Total triples:           {len(reorganized_triples)}")
    print(f"Total unique entities:   {stats['total_entities']}")
    print(f"Swapped entities:        {stats['swapped_entities']}")
    print(f"Unchanged entities:      {stats['unchanged_entities']}")
    print(f"Swap percentage:         {stats['swap_percentage']:.1f}%")
    print("\nEntity type distribution:")
    for entity_type, count in sorted(stats['type_counts'].items()):
        if entity_type == 'unknown':
            print(f"  {entity_type:20s}: {count} (NOT swapped - see unknown_entities.txt)")
        else:
            print(f"  {entity_type:20s}: {count}")
    print("="*60)
    
    if args.verbose:
        print("\nConfiguration used:")
        print(f"  Preserve types: {config.preserve_types}")
        print(f"  Swap subjects: {config.swap_subjects}")
        print(f"  Swap objects: {config.swap_objects}")
        print(f"  Swap relationships: {config.swap_relationships}")
        print(f"  Shuffle percentage: {config.shuffle_percentage * 100:.0f}%")


if __name__ == "__main__":
    main()
