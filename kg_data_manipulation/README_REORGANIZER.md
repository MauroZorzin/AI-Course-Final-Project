# Knowledge Graph Reorganizer

A sophisticated tool for reorganizing knowledge graphs by shuffling entities while maintaining complete consistency and structural integrity.

## 🎯 Core Concept

The reorganizer **swaps entities** in your knowledge graph while ensuring:
- ✅ **Complete consistency**: If "Movie A" becomes "Movie X", it changes EVERYWHERE
- ✅ **Type preservation**: Numbers swap with numbers, names with names, titles with titles
- ✅ **Structure preservation**: All relationships remain intact
- ✅ **Bijection**: One-to-one mapping (no collisions)

### Example

**Original:**
```
The Dark Horse|directed_by|Alfred E. Green
The Dark Horse|starred_actors|Bette Davis
The Dark Horse|release_year|1932
The Sentinel|directed_by|Clark Johnson
The Sentinel|release_year|2004
```

**Reorganized:**
```
The Sentinel|directed_by|Clark Johnson  ← Swapped!
The Sentinel|starred_actors|Bette Davis  ← Consistent!
The Sentinel|release_year|1976          ← Year swapped with year!
The Dark Horse|directed_by|Alfred E. Green  ← Swapped!
The Dark Horse|release_year|1847           ← Year swapped with year!
```

Notice:
- "The Dark Horse" ↔ "The Sentinel" (titles with titles)
- 1932 ↔ 1847, 2004 ↔ 1976 (years with years)
- All relationships stay connected to the right entities

## 🌟 Key Features

### 1. **Entity Type Detection**
Automatically detects and categorizes:
- **Numbers**: 42, 3.14, 100
- **Years**: 1932, 2004, 1998
- **Person Names**: "Michael Douglas", "Bette Davis"
- **Titles**: "The Dark Horse", "Dirty Filthy Love"
- **Tags**: lowercase descriptors
- **Genres**: Drama, Comedy, Action
- **Languages**: French, English, Spanish

### 2. **Type-Consistent Swapping**
- Numbers only swap with numbers
- Years only swap with years (same magnitude)
- Person names only swap with person names
- Titles only swap with titles
- Can be disabled for complete randomization

### 3. **Complete Consistency**
- Every occurrence of an entity is swapped
- No partial swaps or inconsistencies
- Maintains all relationships

### 4. **Configurable Swapping**
- Choose what to swap: subjects, objects, relationships
- Control swap percentage (shuffle 50%, 75%, 100%)
- Reproducible with seed

### 5. **Verification Tools**
- Built-in consistency checker
- Separate verification script
- Detailed reports

## 📦 Installation

```bash
# No external dependencies - uses only Python standard library
python kg_reorganizer.py --help
```

## 🚀 Usage Examples

### Basic Usage
```bash
# Simple reorganization
python kg_reorganizer.py input.txt output.txt --seed 42
```

### Type-Consistent Swapping (Recommended)
```bash
# Swap with type preservation (default)
python kg_reorganizer.py movies.txt movies_reorganized.txt \
  --preserve-types \
  --seed 42 \
  --verbose
```

### Partial Shuffling
```bash
# Shuffle only 50% of entities
python kg_reorganizer.py input.txt output.txt \
  --shuffle-percentage 0.5 \
  --seed 42
```

### Swap Subjects Only
```bash
# Keep objects unchanged, only swap subjects
python kg_reorganizer.py input.txt output.txt \
  --swap-subjects \
  --no-swap-objects \
  --seed 42
```

### Complete Randomization
```bash
# Disable type preservation (swap anything with anything)
python kg_reorganizer.py input.txt output.txt \
  --no-preserve-types \
  --seed 42
```

### Swap Relationships Too
```bash
# Also swap relationship names
python kg_reorganizer.py input.txt output.txt \
  --swap-relationships \
  --seed 42
```

### With Verification
```bash
# Reorganize and verify
python kg_reorganizer.py input.txt output.txt --seed 42 --verbose
python kg_verifier.py input.txt output.txt --mapping reorganization_mapping.txt
```

## 🔧 Configuration Options

### What to Swap
| Flag | Default | Description |
|------|---------|-------------|
| `--swap-subjects` | True | Swap subject entities |
| `--no-swap-subjects` | - | Don't swap subjects |
| `--swap-objects` | True | Swap object entities |
| `--no-swap-objects` | - | Don't swap objects |
| `--swap-relationships` | False | Swap relationship names |

### Type Preservation
| Flag | Default | Description |
|------|---------|-------------|
| `--preserve-types` | True | Keep types consistent |
| `--no-preserve-types` | - | Allow cross-type swapping |
| `--swap-numbers-only-with-numbers` | True | Numbers ↔ numbers |
| `--swap-years-only-with-years` | True | Years ↔ years |
| `--swap-names-only-with-names` | True | Names ↔ names |
| `--swap-titles-only-with-titles` | True | Titles ↔ titles |

### Detection Options
| Flag | Default | Description |
|------|---------|-------------|
| `--detect-multi-word-titles` | True | Detect multi-word titles |
| `--detect-person-names` | True | Detect person names |
| `--year-min` | 1800 | Minimum year value |
| `--year-max` | 2100 | Maximum year value |

### Randomization
| Flag | Default | Description |
|------|---------|-------------|
| `--seed` | None | Random seed for reproducibility |
| `--shuffle-percentage` | 1.0 | Fraction of entities to shuffle (0.0-1.0) |

### Output Options
| Flag | Default | Description |
|------|---------|-------------|
| `--mapping-file` | reorganization_mapping.txt | Swap mapping file |
| `--full-mapping-file` | full_mapping.txt | Complete mapping |
| `--type-analysis-file` | type_analysis.txt | Type analysis |
| `--save-full-mapping` | False | Save all mappings |
| `--save-type-analysis` | False | Save type details |
| `--verbose` / `-v` | False | Verbose output |

## 📊 Output Files

### 1. Reorganized Knowledge Graph
Same format as input with swapped entities:
```
New_Subject|relationship|New_Object
```

### 2. Mapping File (reorganization_mapping.txt)
Shows only the entities that were swapped:
```
Original|Swapped_To|Type
The Dark Horse|The Sentinel|title
Alfred E. Green|Clark Johnson|person_name
1932|1847|year
```

### 3. Full Mapping File (optional)
Includes all entities, even unchanged:
```
Original|Swapped_To|Type|Changed
The Dark Horse|The Sentinel|title|Yes
Bette Davis|Bette Davis|person_name|No
...
```

### 4. Type Analysis File (optional)
Detailed breakdown by type:
```
Entity Type Analysis
============================================================

TITLE (4 entities):
------------------------------------------------------------
  The Dark Horse → The Sentinel
  The Sentinel → The Dark Horse
  Dirty Filthy Love → Dirty Filthy Love
  ...
```

## 🔍 Verification

### Using the Verifier
```bash
python kg_verifier.py original.txt reorganized.txt \
  --mapping reorganization_mapping.txt \
  --report verification_report.txt
```

### Verification Checks

The verifier performs:
1. **Triple Count**: Same number of triples
2. **Relationship Preservation**: Relationship distribution unchanged
3. **Entity Consistency**: Each entity swaps consistently everywhere
4. **Structure Preservation**: Graph structure maintained
5. **Type Consistency**: Types preserved (numbers with numbers, etc.)
6. **No Duplicates**: No duplicate triples created
7. **Mapping Coverage**: Mapping file covers all changes
8. **Bijection Property**: One-to-one mapping (no collisions)

### Verification Output
```
============================================================
VERIFICATION RESULTS
============================================================

✓ PASSED CHECKS:
  ✓ Triple count matches: 26 triples
  ✓ Consistency verified: All 30 entities map consistently
  ✓ Graph structure preserved
  ✓ Type consistency maintained
  ✓ No duplicate triples found
  ✓ Mapping covers all 15 changed entities
  ✓ Mapping is a proper bijection

✓ ALL VERIFICATIONS PASSED
The reorganized graph is consistent and valid!
============================================================
```

## 💡 Use Cases

### 1. Data Anonymization
```bash
# Create anonymized version while preserving structure
python kg_reorganizer.py sensitive.txt public.txt \
  --preserve-types \
  --seed 12345
```

### 2. Test Data Generation
```bash
# Create test datasets from production data
python kg_reorganizer.py production.txt test.txt \
  --shuffle-percentage 0.8 \
  --seed 42
```

### 3. Data Augmentation
```bash
# Create variations for machine learning
for i in {1..10}; do
  python kg_reorganizer.py original.txt "augmented_$i.txt" --seed $i
done
```

### 4. Privacy-Preserving Research
```bash
# Share research data with entity privacy
python kg_reorganizer.py research.txt public_research.txt \
  --preserve-types \
  --seed 99999
```

## 🎨 Entity Type Examples

| Type | Examples |
|------|----------|
| **YEAR** | 1932, 2004, 1998, 2015 |
| **NUMBER** | 42, 3.14, 100, 99.9 |
| **PERSON_NAME** | Michael Douglas, Bette Davis, Clark Johnson |
| **TITLE** | The Dark Horse, Dirty Filthy Love, The Sentinel |
| **TAG** | revenge, wedding, black, action |
| **GENRE** | Drama, Comedy, Action, Thriller |
| **LANGUAGE** | French, English, Spanish, Japanese |
| **UNKNOWN** | Anything else |

## 🔄 How Swapping Works

### Type-Consistent Swapping (Default)
```
Titles:
  The Dark Horse ↔ The Sentinel
  Dirty Filthy Love ↔ Dirty Filthy Love (identity)

Person Names:
  Alfred E. Green ↔ Clark Johnson
  Bette Davis ↔ Michael Douglas

Years:
  1932 ↔ 1847
  2004 ↔ 1976
```

### Cross-Type Swapping (--no-preserve-types)
```
Mixed swapping:
  The Dark Horse ↔ 1932
  Alfred E. Green ↔ Drama
  2004 ↔ Michael Douglas
  
⚠️ Not recommended - breaks semantic meaning!
```

## ⚠️ Important Notes

1. **Consistency is Guaranteed**: Every occurrence of an entity is swapped
2. **Bijection Property**: Each entity maps to exactly one other entity
3. **Structure Preserved**: All relationships remain intact
4. **Type Safety**: By default, types are preserved
5. **Reproducibility**: Use `--seed` for consistent results

## 🐛 Troubleshooting

### Issue: Types not detected correctly
**Solution**: Adjust detection parameters or check your data format

### Issue: Want different swapping behavior
**Solution**: Use `--no-preserve-types` or disable specific type constraints

### Issue: Need reproducible results
**Solution**: Always use `--seed` parameter

### Issue: Verification fails
**Solution**: Check the error messages from the verifier - it will tell you exactly what's wrong

## 📝 Examples with Your Movie Data

```bash
# Basic reorganization
python kg_reorganizer.py movies.txt movies_reorg.txt --seed 42 --verbose

# Partial shuffle (50%)
python kg_reorganizer.py movies.txt movies_reorg_50.txt \
  --shuffle-percentage 0.5 --seed 42

# Verify
python kg_verifier.py movies.txt movies_reorg.txt \
  --mapping reorganization_mapping.txt \
  --report verification.txt
```

## 🤝 Comparison with Obfuscator

| Feature | Obfuscator | Reorganizer |
|---------|-----------|-------------|
| Purpose | Replace with random strings | Shuffle existing entities |
| Entities | New random values | Same entities, different positions |
| Reversible | Via mapping file | Via mapping file |
| Type preservation | Optional | Default |
| Verification | Manual | Built-in + separate tool |

## 📚 Additional Resources

- See `QUICKSTART_REORGANIZER.md` for quick commands
- See verification examples in `kg_verifier.py --help`
- Check example outputs in the demo files

## 🎓 Best Practices

1. **Always use a seed** for reproducibility
2. **Verify after reorganization** using the verifier
3. **Keep type preservation enabled** unless you have a specific reason
4. **Save the mapping file** for reference
5. **Test with small datasets** first

## License

MIT License - Feel free to use and modify as needed.
