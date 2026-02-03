# show_entities.py
import sys
from collections import Counter

kg_file = sys.argv[1] if len(sys.argv) > 1 else '../MetaQA/kb.txt'

entities = []
with open(kg_file, 'r', encoding='utf-8') as f:
    for line in f:
        parts = line.strip().split('|')
        if len(parts) == 3:
            entities.append(parts[0])

# Show most common entities (these are good starting points)
counter = Counter(entities)
print("Top 10 entities in your KG:")
for entity, count in counter.most_common(100):
    print(f"  {entity} ({count} connections)")