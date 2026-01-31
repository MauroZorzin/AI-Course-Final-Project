# Quick Reference Guide

## Most Common Commands

### 1. Basic Obfuscation (Recommended)
```bash
python kg_obfuscator_advanced.py input.txt output.txt \
  --strategy word_like \
  --min-length 5 --max-length 12 \
  --multi-word-strategy combined \
  --seed 42
```
**Result**: Realistic word-like replacements, multi-word entities treated as single units

### 2. Separate Multi-Word Entities
```bash
python kg_obfuscator_advanced.py input.txt output.txt \
  --multi-word-strategy separate \
  --seed 42
```
**Result**: "The Dark Horse" → "Nidepo Fikem Tagewi" (each word separately)

### 3. Keep Numbers Original
```bash
python kg_obfuscator_advanced.py input.txt output.txt \
  --no-obfuscate-numbers \
  --seed 42
```
**Result**: Years and numbers stay unchanged

### 4. Preserve Number Magnitude
```bash
python kg_obfuscator_advanced.py input.txt output.txt \
  --preserve-number-magnitude \
  --seed 42
```
**Result**: 1932 → 1847 (stays in 1000s), 2004 → 1976 (stays in 2000s)

### 5. Maximum Obfuscation
```bash
python kg_obfuscator_advanced.py input.txt output.txt \
  --obfuscate-relationships \
  --strategy alphanumeric \
  --no-preserve-number-magnitude \
  --seed 42
```
**Result**: Everything obfuscated including relationship names

### 6. Only Obfuscate Objects
```bash
python kg_obfuscator_advanced.py input.txt output.txt \
  --no-obfuscate-subjects \
  --seed 42
```
**Result**: Subjects stay original, only objects change

### 7. Sophisticated Realistic
```bash
python kg_obfuscator_advanced.py input.txt output.txt \
  --strategy-weights "word_like:0.5,pronounceable:0.3,readable:0.2" \
  --length-distribution normal \
  --add-hyphens --hyphen-probability 0.15 \
  --multi-word-strategy separate \
  --seed 42
```
**Result**: Mixed strategies, natural length distribution, some hyphens

## Strategy Comparison

| Strategy | Example Output | Best For |
|----------|---------------|----------|
| `readable` | Nidogepi | Quick, readable results |
| `random_alpha` | xkqpwmvz | Maximum randomness |
| `alphanumeric` | ab3x9k2p | Including numbers in strings |
| `pronounceable` | Brachtor | Easy to say aloud |
| `mixed_case` | NiDoGePi | Varied appearance |
| `word_like` | Brachness | Most realistic |

## Multi-Word Strategy Comparison

| Strategy | Input | Output | Use Case |
|----------|-------|--------|----------|
| `combined` | The Dark Horse | Dunuweto | Treat as single entity |
| `separate` | The Dark Horse | Nidepo Fikem Tagewi | Keep word structure |
| `preserve` | The Dark Horse | The Dark Horse | Don't change |

## Length Distribution Comparison

| Distribution | Behavior | Example Lengths |
|-------------|----------|-----------------|
| `uniform` | All lengths equal probability | 5,8,12,5,10,7,12,6 |
| `normal` | Favors middle lengths | 7,8,9,8,7,9,8,9 |
| `weighted` | Similar to normal but stronger | 8,8,9,8,7,9,9,8 |

## Common Parameter Combinations

### Data Anonymization
```bash
--strategy word_like \
--preserve-number-magnitude \
--multi-word-strategy combined \
--seed <your-seed>
```

### Testing & Development
```bash
--strategy-weights "word_like:0.4,readable:0.6" \
--length-distribution normal \
--preserve-number-magnitude \
--seed 42
```

### Research Dataset
```bash
--strategy pronounceable \
--no-obfuscate-relationships \
--preserve-number-magnitude \
--multi-word-strategy separate
```

### Maximum Privacy
```bash
--obfuscate-relationships \
--strategy alphanumeric \
--no-preserve-number-magnitude \
--min-length 8 --max-length 15
```

## Troubleshooting Quick Fixes

### Problem: Multi-word entities not changing
**Fix**: Check `--multi-word-strategy` is NOT set to `preserve`

### Problem: Numbers becoming text
**Fix**: Remove `--no-obfuscate-numbers` flag (obfuscation is default)

### Problem: Years too random (1932 → 8567)
**Fix**: Add `--preserve-number-magnitude` flag

### Problem: Want same results each time
**Fix**: Always use `--seed 42` (or any consistent number)

### Problem: Strings too similar
**Fix**: Use `alphanumeric` or `random_alpha` strategy

### Problem: Need more realistic names
**Fix**: Use `--strategy word_like` or mix with weights

## Output Files

After running, you get:

1. **output.txt** - Obfuscated knowledge graph
2. **mapping.txt** - Original → Replacement mappings
   - Add `--reverse-mapping` for Replacement → Original

## Key Differences from Original Script

| Feature | Original | Enhanced |
|---------|----------|----------|
| Multi-word | ❌ Ignored | ✅ 3 strategies |
| Numbers | Text | Numbers |
| Strategies | 2 | 6 + mixing |
| Length | Fixed | Min-max + distributions |
| Selective | Objects only | All components |

## Quick Command Builder

Start with:
```bash
python kg_obfuscator_advanced.py INPUT OUTPUT
```

Add options:
- Want realistic? → `--strategy word_like`
- Keep structure? → `--multi-word-strategy separate`
- Keep years valid? → `--preserve-number-magnitude`
- Reproducible? → `--seed 42`
- Keep relationships? → `--no-obfuscate-relationships`
- Add variety? → `--strategy-weights "word_like:0.5,pronounceable:0.5"`

## Help Command
```bash
python kg_obfuscator_advanced.py --help
```

## Examples with Your Data

Your input has:
- Multi-word subjects: "The Bride Wore Black", "Dirty Filthy Love"
- Multi-word objects: "Adrian Shergold", "françois truffaut"
- Numbers: 1932, 2004

### Good command for your data:
```bash
python kg_obfuscator_advanced.py movies.txt movies_obfuscated.txt \
  --strategy word_like \
  --min-length 6 --max-length 12 \
  --multi-word-strategy combined \
  --preserve-number-magnitude \
  --seed 42 \
  --verbose
```

This will:
- ✅ Obfuscate "The Bride Wore Black" → single word
- ✅ Obfuscate "Adrian Shergold" → single word
- ✅ Keep 1932 → ~1900s, 2004 → ~2000s
- ✅ Create realistic-looking names
- ✅ Be reproducible with seed