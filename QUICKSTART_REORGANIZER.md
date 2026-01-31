# Quick Start Guide - Knowledge Graph Reorganizer

## 🚀 Most Common Commands

### 1. Basic Reorganization (Recommended)
```bash
python kg_reorganizer.py input.txt output.txt --seed 42 --verbose
```
**Result**: Shuffles all entities while preserving types

### 2. With Verification
```bash
# Step 1: Reorganize
python kg_reorganizer.py input.txt output.txt --seed 42 --verbose

# Step 2: Verify
python kg_verifier.py input.txt output.txt \
  --mapping reorganization_mapping.txt \
  --report verification.txt
```
**Result**: Reorganizes and verifies consistency

### 3. Partial Shuffle (50%)
```bash
python kg_reorganizer.py input.txt output.txt \
  --shuffle-percentage 0.5 \
  --seed 42
```
**Result**: Only shuffles half of the entities

### 4. Complete Randomization
```bash
python kg_reorganizer.py input.txt output.txt \
  --no-preserve-types \
  --seed 42
```
**Result**: Entities can swap with any other entity (ignores types)

### 5. Swap Subjects Only
```bash
python kg_reorganizer.py input.txt output.txt \
  --swap-subjects \
  --no-swap-objects \
  --seed 42
```
**Result**: Only movie titles swap, actors/directors stay the same

### 6. Include Relationships
```bash
python kg_reorganizer.py input.txt output.txt \
  --swap-relationships \
  --seed 42
```
**Result**: Even relationship names get swapped

### 7. With Full Analysis
```bash
python kg_reorganizer.py input.txt output.txt \
  --seed 42 \
  --verbose \
  --save-full-mapping \
  --save-type-analysis
```
**Result**: Creates detailed analysis files

## 📊 Understanding the Output

### Reorganized Graph
```
# Original
The Dark Horse|directed_by|Alfred E. Green
Dirty Filthy Love|directed_by|Adrian Shergold

# After reorganization
Dirty Filthy Love|directed_by|Alfred E. Green  ← Swapped!
The Dark Horse|directed_by|Adrian Shergold    ← Consistent!
```

### Mapping File
Shows what swapped with what:
```
Original|Swapped_To|Type
The Dark Horse|Dirty Filthy Love|title
Dirty Filthy Love|The Dark Horse|title
Alfred E. Green|Adrian Shergold|person_name
Adrian Shergold|Alfred E. Green|person_name
```

## 🔍 Entity Type Detection

The script automatically detects:

| Type | Examples | Swaps With |
|------|----------|------------|
| **YEAR** | 1932, 2004 | Other years |
| **NUMBER** | 42, 100 | Other numbers |
| **PERSON_NAME** | Michael Douglas | Other person names |
| **TITLE** | The Dark Horse | Other titles |
| **TAG** | revenge, wedding | Other tags |
| **GENRE** | Drama, Comedy | Other genres |
| **LANGUAGE** | French, English | Other languages |

## ✅ Verification Checklist

After reorganization, the verifier checks:

1. ✓ Same number of triples
2. ✓ Each entity swaps consistently everywhere
3. ✓ Graph structure preserved
4. ✓ Types maintained (numbers with numbers, etc.)
5. ✓ No duplicate triples
6. ✓ One-to-one mapping (bijection)

## 🎯 Common Use Cases

### Anonymize Data
```bash
python kg_reorganizer.py sensitive.txt anonymous.txt \
  --preserve-types --seed 99999
```

### Create Test Data
```bash
python kg_reorganizer.py production.txt test.txt \
  --shuffle-percentage 0.7 --seed 42
```

### Data Augmentation (10 variants)
```bash
for i in {1..10}; do
  python kg_reorganizer.py data.txt "variant_$i.txt" --seed $i
done
```

## ⚙️ Key Parameters

| Parameter | What It Does | Example |
|-----------|--------------|---------|
| `--seed 42` | Reproducible results | Always same output |
| `--shuffle-percentage 0.5` | Partial shuffle | Only 50% entities swap |
| `--preserve-types` | Type-safe swapping | Years with years |
| `--no-preserve-types` | Any swaps | Years with names (chaos!) |
| `--swap-subjects` | Swap titles | Movie names change |
| `--no-swap-objects` | Keep objects | Actors/directors stay same |
| `--swap-relationships` | Swap relations | directed_by ↔ written_by |

## 🐛 Troubleshooting

### Problem: Want consistent results
**Fix**: Use `--seed 42`

### Problem: Too much randomization
**Fix**: Use `--shuffle-percentage 0.5` (or lower)

### Problem: Wrong entity types detected
**Fix**: Check your data format or adjust `--year-min`/`--year-max`

### Problem: Need to verify
**Fix**: Run `python kg_verifier.py original.txt reorganized.txt --mapping reorganization_mapping.txt`

### Problem: Verification fails
**Fix**: The verifier will tell you exactly what's wrong - read the error messages

## 📈 Statistics Explanation

```
Total unique entities:   30    ← Different entities in your graph
Swapped entities:        28    ← How many actually changed
Unchanged entities:      2     ← How many stayed the same
Swap percentage:         93.3% ← Percentage that changed
```

## 💡 Pro Tips

1. **Always verify** after reorganization
2. **Use seeds** for reproducibility
3. **Check type analysis** if results look wrong
4. **Start with small shuffle percentage** to test
5. **Save all mapping files** for reference

## 🔄 Workflow Example

```bash
# 1. Reorganize
python kg_reorganizer.py movies.txt movies_reorg.txt \
  --seed 42 \
  --verbose \
  --save-type-analysis

# 2. Check the output
head movies_reorg.txt

# 3. Review the mapping
cat reorganization_mapping.txt

# 4. Verify consistency
python kg_verifier.py movies.txt movies_reorg.txt \
  --mapping reorganization_mapping.txt \
  --report verification.txt

# 5. Check verification report
cat verification.txt
```

## 🎓 Quick Reference

### Reorganize with defaults
```bash
python kg_reorganizer.py input.txt output.txt --seed 42
```

### Verify
```bash
python kg_verifier.py input.txt output.txt --mapping reorganization_mapping.txt
```

### Help
```bash
python kg_reorganizer.py --help
python kg_verifier.py --help
```

## 📝 Example with Your Movie Data

Your data has:
- Titles: "The Dark Horse", "Dirty Filthy Love", "The Bride Wore Black", "The Sentinel"
- Person names: "Alfred E. Green", "Bette Davis", "Michael Douglas", etc.
- Years: 1932, 2004
- Tags: revenge, wedding, bd-r, etc.

### Perfect command:
```bash
python kg_reorganizer.py movies.txt movies_reorg.txt \
  --preserve-types \
  --seed 42 \
  --verbose \
  --save-type-analysis
```

This will:
- ✅ Swap titles with titles
- ✅ Swap person names with person names  
- ✅ Swap years with years (1932 ↔ 2004)
- ✅ Swap tags with tags
- ✅ Keep all relationships intact
- ✅ Maintain complete consistency

### Then verify:
```bash
python kg_verifier.py movies.txt movies_reorg.txt \
  --mapping reorganization_mapping.txt \
  --report verification.txt
```

You'll see:
```
✓ ALL VERIFICATIONS PASSED
The reorganized graph is consistent and valid!
```

## 🎉 Success Indicators

When everything works correctly, you'll see:

1. **Reorganizer output**: "REORGANIZATION COMPLETE"
2. **Mapping file created**: reorganization_mapping.txt
3. **Verifier passes**: "✓ ALL VERIFICATIONS PASSED"
4. **No errors**: Exit code 0

## 🔗 Related Files

- `README_REORGANIZER.md` - Complete documentation
- `kg_reorganizer.py` - Main script
- `kg_verifier.py` - Verification script
- `reorganization_mapping.txt` - Output mapping
- `type_analysis.txt` - Type details (if requested)
