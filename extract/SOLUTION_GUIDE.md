# Complete Knowledge Graph Path Extraction & Question Generation Solution

## Overview

This solution provides **three powerful approaches** to extract paths from your Knowledge Graph and generate natural language questions. Choose the approach that best fits your needs.

## 🎯 The Problem You're Solving

You have a KG like this:
```
Kismet|directed_by|William Dieterle
Kismet|written_by|Edward Knoblock
Kismet|starred_actors|Marlene Dietrich
```

And you want to:
1. **Index it** for fast queries
2. **Extract paths** (e.g., Kismet → Marlene Dietrich → other movies)
3. **Generate questions** from those paths

## 🛠️ Three Solution Approaches

### Approach 1: Direct Extraction (Recommended for Simple Cases)

**Best for:** Small KGs, specific entity queries, exploration

**Tools:** `kg_path_extractor.py`

```bash
# Find all 2-hop paths from Kismet
./kg_path_extractor.py --load kg.txt \
  --n-hop --start "Kismet" --length 2 \
  --output paths.json

# Find paths between specific entities
./kg_path_extractor.py --load kg.txt \
  --find-paths --start "Kismet" --end "Josef von Sternberg"

# Find paths matching a pattern
./kg_path_extractor.py --load kg.txt \
  --pattern "directed_by,starred_actors"
```

**Output:** JSON with detailed path information

**Pros:**
- ✅ Fast and simple
- ✅ Multiple query types
- ✅ Rich path metadata

**Cons:**
- ❌ Instance paths (not typed schemas)
- ❌ Requires type mapping for questions

---

### Approach 2: Full Pipeline with Type Mapping

**Best for:** Medium KGs, when you need both paths and questions

**Tools:** `kg_path_extractor.py` + `kg_type_mapper.py` + `kg_path_question_generator.py`

```bash
#!/bin/bash
# Step 1: Extract instance paths
./kg_path_extractor.py --load kg.txt \
  --n-hop --start "Kismet" --length 2 \
  --output instance_paths.json

# Step 2: Convert to typed schema paths
./kg_type_mapper.py --kg kg.txt \
  --paths instance_paths.json \
  --output schema_paths.json

# Step 3: Generate questions
./kg_path_question_generator.py --input schema_paths.json \
  --output questions.json
```

**Pros:**
- ✅ Complete control over each step
- ✅ Can inspect intermediates
- ✅ Type inference from KG structure

**Cons:**
- ❌ Three-step process
- ❌ Manual pipeline management

---

### Approach 3: Integrated Workflow (Recommended for Production)

**Best for:** Large KGs, automated workflows, production systems

**Tools:** `kg_workflow.py` (combines all tools)

```bash
# One command for everything!
./kg_workflow.py --kg kg.txt \
  --n-hop --start "Kismet" --length 2 \
  --limit 10 \
  --output results.json
```

**Output:** JSON with paths AND questions

**Pros:**
- ✅ Single command
- ✅ Integrated pipeline
- ✅ Automatic type inference

**Cons:**
- ❌ Currently requires typed entities in KG
- ❌ Less granular control

---

## 📊 Comparison Matrix

| Feature | Approach 1 | Approach 2 | Approach 3 |
|---------|-----------|------------|------------|
| Commands needed | 1 | 3 | 1 |
| Type inference | ❌ | ✅ | ⚠️ Limited |
| Path metadata | ✅ Full | ✅ Full | ✅ Full |
| Questions | ❌ | ✅ | ✅ |
| Flexibility | High | Highest | Medium |
| Ease of use | Easy | Medium | Easiest |
| Best for | Exploration | Custom workflows | Production |

---

## 🚀 Quick Start Recipes

### Recipe 1: Explore Movie Connections

```bash
# What movies are connected to Kismet within 2 hops?
./kg_path_extractor.py --load kg.txt \
  --n-hop --start "Kismet" --length 2 \
  --limit 20
```

### Recipe 2: Find Director-Actor Patterns

```bash
# Find all cases where directors also acted
./kg_path_extractor.py --load kg.txt \
  --pattern "directed_by,starred_actors" \
  --output director_actors.json
```

### Recipe 3: Generate Questions for All 2-Hop Paths

```bash
# Complete workflow
./kg_path_extractor.py --load kg.txt \
  --n-hop --start "Kismet" --length 2 \
  --output paths.json

./kg_type_mapper.py --kg kg.txt \
  --schema kg_schema_typed_arcs.txt \
  --paths paths.json \
  --output typed.json

./kg_path_question_generator.py --input typed.json
```

### Recipe 4: Batch Process Multiple Entities

```bash
#!/bin/bash
# Process multiple starting entities
for entity in "Kismet" "The Blue Angel" "Morocco"; do
    echo "Processing $entity..."
    ./kg_path_extractor.py --load kg.txt \
      --n-hop --start "$entity" --length 2 \
      --limit 5 \
      --output "${entity// /_}_paths.json"
done
```

---

## 🎓 Understanding the Components

### Component 1: kg_path_extractor.py

**Purpose:** Index and query your KG

**Key Features:**
- Triple indexing (forward, backward, relation)
- BFS path finding
- Pattern matching
- N-hop exploration

**Query Types:**

| Query | Command | Use Case |
|-------|---------|----------|
| Statistics | `--stats` | Understand KG structure |
| Entity Info | `--entity-info "X"` | Explore entity connections |
| Find Paths | `--find-paths --start X --end Y` | Shortest paths |
| Pattern | `--pattern "rel1,rel2"` | Find specific patterns |
| N-Hop | `--n-hop --start X --length N` | Explore neighborhood |

### Component 2: kg_type_mapper.py

**Purpose:** Convert instance paths to typed schema paths

**How it works:**
1. Analyzes KG structure
2. Infers entity types from relations
3. Maps instances to types

**Example:**
```
Input:  ["Kismet", "directed_by", "William Dieterle"]
Output: ["title", "directed_by", "person_name"]
```

### Component 3: kg_path_question_generator.py

**Purpose:** Generate questions from typed paths

**Example:**
```
Input:  ["title", "directed_by", "person_name"]
Output: "Who are associated with directors of the movie {title}?"
```

### Component 4: kg_workflow.py

**Purpose:** End-to-end automation

**Combines:** All three components in one command

---

## 📝 Common Use Cases

### Use Case 1: Dataset Exploration

**Goal:** Understand what's in your KG

```bash
# Step 1: Get statistics
./kg_path_extractor.py --load kg.txt --stats

# Step 2: Explore a key entity
./kg_path_extractor.py --load kg.txt --entity-info "Kismet"

# Step 3: Find interesting patterns
./kg_path_extractor.py --load kg.txt \
  --pattern "directed_by,starred_actors" --limit 10
```

### Use Case 2: Question Generation for QA Systems

**Goal:** Generate training questions from KG

```bash
# Extract diverse 2-hop paths
./kg_path_extractor.py --load kg.txt \
  --n-hop --start "Kismet" --length 2 --limit 100 \
  --output paths.json

# Map to types
./kg_type_mapper.py --kg kg.txt \
  --schema kg_schema.txt \
  --paths paths.json --output typed.json

# Generate questions
./kg_path_question_generator.py --input typed.json \
  --output training_questions.json
```

### Use Case 3: Knowledge Graph Validation

**Goal:** Find missing or unusual connections

```bash
# Find all unique relation patterns
./kg_path_extractor.py --load kg.txt \
  --pattern "directed_by,directed_by" --limit 100

# This finds cases like: Person -> Movie -> Person
# Useful for finding data quality issues
```

### Use Case 4: Recommendation System Paths

**Goal:** Extract paths for recommendation explanations

```bash
# Find paths between user's liked item and recommendations
./kg_path_extractor.py --load kg.txt \
  --find-paths --start "Movie_A" --end "Movie_B" \
  --max-length 3
```

---

## 🔧 Advanced Configuration

### Custom Schema Definition

If you have a schema file:
```
SUBJECT_TYPE|RELATIONSHIP|OBJECT_TYPE|FREQUENCY
title|directed_by|person_name|15781
title|starred_actors|person_name|33386
```

Use it for better type inference:
```bash
./kg_type_mapper.py --kg kg.txt \
  --schema kg_schema_typed_arcs.txt \
  --paths instance_paths.json \
  --output typed_paths.json
```

### Performance Tuning

For large KGs:

```bash
# Limit results to avoid memory issues
./kg_path_extractor.py --load huge_kg.txt \
  --n-hop --start "Entity" --length 2 \
  --limit 1000  # Only return first 1000 paths

# Use shorter max path lengths
./kg_path_extractor.py --load huge_kg.txt \
  --find-paths --start A --end B \
  --max-length 2  # Instead of default 3
```

### Batch Processing Script

```bash
#!/bin/bash
# process_all_entities.sh

KG_FILE="my_kg.txt"
OUTPUT_DIR="results"
mkdir -p $OUTPUT_DIR

# Get all unique entities
entities=$(cut -d'|' -f1,3 $KG_FILE | tr '|' '\n' | sort -u)

# Process each entity
for entity in $entities; do
    echo "Processing: $entity"
    
    # Extract paths
    ./kg_path_extractor.py --load $KG_FILE \
      --n-hop --start "$entity" --length 2 \
      --limit 10 \
      --output "$OUTPUT_DIR/${entity// /_}_paths.json"
done

echo "Complete! Check $OUTPUT_DIR/"
```

---

## 🐛 Troubleshooting

### Problem: No paths found

**Possible causes:**
1. Entities don't exist in KG
2. Path length too short
3. No connection exists

**Solutions:**
```bash
# Check entity exists
./kg_path_extractor.py --load kg.txt --entity-info "EntityName"

# Try longer paths
./kg_path_extractor.py --load kg.txt \
  --find-paths --start A --end B --max-length 4

# Check KG stats
./kg_path_extractor.py --load kg.txt --stats
```

### Problem: Type inference errors

**Cause:** Unknown entity types

**Solutions:**
1. Provide schema file: `--schema kg_schema.txt`
2. Check type mappings manually
3. Add type hints to your KG

### Problem: Questions are awkward

**Cause:** Grammar normalization needs tuning

**Solution:** Edit `kg_path_question_generator.py` grammar rules

### Problem: Too many results

**Solution:** Use `--limit`:
```bash
./kg_path_extractor.py --load kg.txt \
  --n-hop --start X --length 2 --limit 50
```

---

## 📦 Complete Example Workflow

Here's a complete end-to-end example:

```bash
#!/bin/bash
# complete_workflow.sh

KG="movie_kg.txt"
ENTITY="Kismet"
LENGTH=2

echo "=== Step 1: Analyze KG ==="
./kg_path_extractor.py --load $KG --stats

echo -e "\n=== Step 2: Explore Entity ==="
./kg_path_extractor.py --load $KG --entity-info "$ENTITY"

echo -e "\n=== Step 3: Extract Paths ==="
./kg_path_extractor.py --load $KG \
  --n-hop --start "$ENTITY" --length $LENGTH \
  --limit 20 \
  --output instance_paths.json

echo -e "\n=== Step 4: Map Types ==="
./kg_type_mapper.py --kg $KG \
  --schema kg_schema_typed_arcs.txt \
  --paths instance_paths.json \
  --output typed_paths.json

echo -e "\n=== Step 5: Generate Questions ==="
./kg_path_question_generator.py --input typed_paths.json \
  --output final_questions.json

echo -e "\n=== Step 6: View Results ==="
python3 -c "
import json
with open('final_questions.json') as f:
    results = json.load(f)
    
successful = [r for r in results if r.get('success')]
print(f'Generated {len(successful)} questions from {len(results)} paths\n')

for i, result in enumerate(successful[:5], 1):
    print(f'{i}. {result[\"question\"]}')
"

echo -e "\n=== Complete! ==="
echo "Results saved to final_questions.json"
```

Make it executable and run:
```bash
chmod +x complete_workflow.sh
./complete_workflow.sh
```

---

## 🎯 Best Practices

### 1. Start Small
- Test with `--limit 10` first
- Explore with `--entity-info` before extracting paths
- Use `--stats` to understand your KG

### 2. Use Schema Files
- Always provide schema when available
- Improves type inference accuracy
- Reduces errors in question generation

### 3. Validate Output
- Check intermediate files
- Review questions for quality
- Adjust grammar rules as needed

### 4. Optimize for Scale
- Use `--limit` for large KGs
- Process entities in batches
- Consider database backends for huge datasets

### 5. Version Control
- Save extraction parameters
- Document query configurations
- Track schema versions

---

## 📚 Additional Resources

- `README.md` - Question generator documentation
- `KG_PATH_EXTRACTOR_README.md` - Path extractor details
- `QUICKSTART.md` - Quick start guide
- `CHANGELOG.md` - Version history

## 🤝 Support

For issues:
1. Check examples in this guide
2. Run with `--verbose` flag
3. Review error messages carefully
4. Test with sample_kg.txt first

---

**Version:** 1.0  
**Last Updated:** January 2026  
**Tools:** kg_path_extractor, kg_type_mapper, kg_path_question_generator, kg_workflow
