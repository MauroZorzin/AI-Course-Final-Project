# Advanced Knowledge Graph Obfuscator

A sophisticated tool for obfuscating knowledge graphs with extensive customization options.

## Key Features

### 🎯 Core Capabilities
- **Multi-word entity handling**: Properly obfuscates subjects like "The Dark Horse" and "Adrian E. Green"
- **Number obfuscation**: Replace numbers with numbers, preserving magnitude if desired
- **Selective obfuscation**: Choose to obfuscate subjects, objects, relationships, or any combination
- **Multiple generation strategies**: 6 different ways to generate random strings
- **Flexible length control**: Configure min/max lengths with different distributions

### 🔧 New Features

#### 1. **String Generation Strategies**
- `readable`: Consonant-vowel pattern (e.g., "Nidogepi")
- `random_alpha`: Pure random letters (e.g., "xkqpwmvz")
- `alphanumeric`: Letters + numbers (e.g., "ab3x9k2p")
- `pronounceable`: Complex phonetic patterns (e.g., "Brachtor")
- `mixed_case`: Random case mixing (e.g., "NiDoGePi")
- `word_like`: Realistic word structure with suffixes (e.g., "Brachness")

#### 2. **Length Distribution Options**
- `uniform`: Equal probability for all lengths in range
- `normal`: Gaussian distribution around the mean
- `weighted`: Favors medium lengths over extremes

#### 3. **Number Handling**
- Obfuscate numbers while preserving magnitude (1932 → 1847)
- Custom number ranges
- Option to preserve or randomize magnitude

#### 4. **Multi-word Strategy**
- `combined`: Treat "The Dark Horse" as single entity
- `separate`: Obfuscate each word independently
- `preserve`: Keep multi-word strings unchanged

#### 5. **Advanced Options**
- Add random hyphens (e.g., "Brach-tor")
- Control hyphen probability
- Capitalization options
- Mixed strategy weights

## Installation

```bash
# No external dependencies required - uses only Python standard library
python kg_obfuscator_advanced.py --help
```

## Usage Examples

### Basic Usage
```bash
# Simple obfuscation with defaults
python kg_obfuscator_advanced.py input.txt output.txt
```

### Length Control
```bash
# Custom length range
python kg_obfuscator_advanced.py input.txt output.txt --min-length 4 --max-length 15

# Use normal distribution for more natural lengths
python kg_obfuscator_advanced.py input.txt output.txt --length-distribution normal

# Weighted distribution (favors medium lengths)
python kg_obfuscator_advanced.py input.txt output.txt --length-distribution weighted
```

### Generation Strategies
```bash
# Use pronounceable strategy
python kg_obfuscator_advanced.py input.txt output.txt --strategy pronounceable

# Use word-like strategy (more realistic)
python kg_obfuscator_advanced.py input.txt output.txt --strategy word_like

# Mixed strategies with custom weights (50% readable, 30% pronounceable, 20% word_like)
python kg_obfuscator_advanced.py input.txt output.txt \
  --strategy-weights "readable:0.5,pronounceable:0.3,word_like:0.2"
```

### Number Obfuscation
```bash
# Obfuscate numbers preserving magnitude (1932 stays ~1900s)
python kg_obfuscator_advanced.py input.txt output.txt --preserve-number-magnitude

# Obfuscate numbers with custom range
python kg_obfuscator_advanced.py input.txt output.txt \
  --number-range-min 1000 --number-range-max 3000

# Don't obfuscate numbers at all
python kg_obfuscator_advanced.py input.txt output.txt --no-obfuscate-numbers
```

### Multi-word Handling
```bash
# Treat multi-word entities as separate words
python kg_obfuscator_advanced.py input.txt output.txt --multi-word-strategy separate

# Preserve multi-word entities
python kg_obfuscator_advanced.py input.txt output.txt --multi-word-strategy preserve

# Combined (default) - treat as single entity
python kg_obfuscator_advanced.py input.txt output.txt --multi-word-strategy combined
```

### Selective Obfuscation
```bash
# Obfuscate only subjects (keep objects original)
python kg_obfuscator_advanced.py input.txt output.txt --no-obfuscate-objects

# Obfuscate everything including relationships
python kg_obfuscator_advanced.py input.txt output.txt --obfuscate-relationships

# Only obfuscate objects
python kg_obfuscator_advanced.py input.txt output.txt \
  --no-obfuscate-subjects --obfuscate-objects
```

### Advanced Styling
```bash
# Add random hyphens to strings
python kg_obfuscator_advanced.py input.txt output.txt --add-hyphens

# Control hyphen probability
python kg_obfuscator_advanced.py input.txt output.txt \
  --add-hyphens --hyphen-probability 0.4

# Don't capitalize first letter
python kg_obfuscator_advanced.py input.txt output.txt --no-capitalize-first
```

### Reproducibility
```bash
# Use seed for reproducible results
python kg_obfuscator_advanced.py input.txt output.txt --seed 42
```

### Complex Example
```bash
# Sophisticated obfuscation with multiple options
python kg_obfuscator_advanced.py movies.txt movies_obfuscated.txt \
  --strategy-weights "pronounceable:0.4,word_like:0.4,readable:0.2" \
  --min-length 5 --max-length 14 \
  --length-distribution normal \
  --multi-word-strategy separate \
  --preserve-number-magnitude \
  --add-hyphens --hyphen-probability 0.15 \
  --seed 42 \
  --verbose
```

## Input Format

The script expects a pipe-delimited format:
```
Subject|Relationship|Object
```

Example:
```
The Dark Horse|directed_by|Alfred E. Green
The Dark Horse|starred_actors|Bette Davis
The Dark Horse|release_year|1932
Dirty Filthy Love|release_year|2004
```

## Output

### Obfuscated Knowledge Graph
Same format as input with obfuscated entities:
```
Nidepo|directed_by|Kibalor
Nidepo|starred_actors|Finokem
Nidepo|release_year|1847
Tagewi|release_year|1976
```

### Mapping File
Shows original → replacement mappings:
```
Original|Replacement
Alfred E. Green|Kibalor
Bette Davis|Finokem
The Dark Horse|Nidepo
1932|1847
2004|1976
```

## Statistics Output

After obfuscation, you'll see:
```
============================================================
OBFUSCATION COMPLETE
============================================================
Total triples:           25
Total mappings:          18
Number mappings:         2
Multi-word mappings:     5
Unique replacements:     18
============================================================
```

## Advanced Use Cases

### 1. Data Anonymization for Sharing
```bash
# Create anonymized dataset for research
python kg_obfuscator_advanced.py sensitive_data.txt public_data.txt \
  --strategy word_like \
  --preserve-number-magnitude \
  --seed 12345
```

### 2. Testing with Realistic Data
```bash
# Generate test data that looks realistic
python kg_obfuscator_advanced.py production_kg.txt test_kg.txt \
  --strategy-weights "word_like:0.6,pronounceable:0.4" \
  --multi-word-strategy separate
```

### 3. Partial Obfuscation
```bash
# Keep relationships and subjects, only obfuscate objects
python kg_obfuscator_advanced.py input.txt output.txt \
  --no-obfuscate-subjects \
  --no-obfuscate-relationships \
  --obfuscate-objects
```

## Command-Line Arguments Reference

### Required
- `input_file`: Input knowledge graph file
- `output_file`: Output obfuscated file

### Output Options
- `--mapping-file`: Mapping file path (default: mapping.txt)
- `--reverse-mapping`: Save obfuscated→original mapping instead

### Length Parameters
- `--min-length`: Minimum string length (default: 5)
- `--max-length`: Maximum string length (default: 12)
- `--length-distribution`: Distribution type (uniform/normal/weighted)

### Generation Strategy
- `--strategy`: Single strategy to use
- `--strategy-weights`: Mixed strategies with weights

### Number Handling
- `--obfuscate-numbers/--no-obfuscate-numbers`: Toggle number obfuscation
- `--number-range-min`: Minimum number value (default: 1900)
- `--number-range-max`: Maximum number value (default: 2100)
- `--preserve-number-magnitude/--no-preserve-number-magnitude`: Toggle magnitude preservation

### Selective Obfuscation
- `--obfuscate-subjects/--no-obfuscate-subjects`
- `--obfuscate-objects/--no-obfuscate-objects`
- `--obfuscate-relationships`

### Advanced Options
- `--add-hyphens`: Add random hyphens
- `--hyphen-probability`: Hyphen probability (0.0-1.0)
- `--capitalize-first/--no-capitalize-first`: Toggle first letter capitalization
- `--multi-word-strategy`: How to handle multi-word entities

### Other
- `--seed`: Random seed for reproducibility
- `--verbose/-v`: Verbose output

## Tips & Best Practices

1. **For realistic obfuscation**: Use `word_like` or `pronounceable` strategies
2. **For maximum uniqueness**: Use `random_alpha` or `alphanumeric`
3. **For readability**: Use `readable` with normal length distribution
4. **For testing**: Always use a `--seed` for reproducible results
5. **For multi-word entities**: Use `separate` strategy to maintain granularity
6. **For numbers**: Use `--preserve-number-magnitude` to maintain statistical properties

## Troubleshooting

### Issue: Collisions in generated strings
**Solution**: Increase `--max-length` or use `alphanumeric` strategy

### Issue: Multi-word entities not obfuscated
**Solution**: Ensure you're using `combined` or `separate` strategy (not `preserve`)

### Issue: Numbers not being obfuscated
**Solution**: Check that `--obfuscate-numbers` is enabled (it's default)

### Issue: Want consistent results across runs
**Solution**: Use `--seed` parameter with the same value

## License

MIT License - Feel free to use and modify as needed.