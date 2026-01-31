#!/usr/bin/env python3
"""
kg_schema_extractor.py

Extracts:
- all arc (relationship) types + frequency
- all node/entity types + frequency
- typed arc patterns (SUBJECT_TYPE, RELATION, OBJECT_TYPE)

Uses the same EntityTypeDetector logic as the KG reorganizer.
"""

import argparse
from collections import defaultdict
from typing import List, Tuple

# --------------------------------------------------
# IMPORT YOUR EXISTING CLASSES
# --------------------------------------------------

from enum import Enum
from dataclasses import dataclass

# ⚠️ COPY these directly from your existing code
# (shortened here for clarity – keep your full logic)

class EntityType(Enum):
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
    preserve_types: bool = True
    year_min: int = 1800
    year_max: int = 2100
    detect_multi_word_titles: bool = True
    detect_person_names: bool = True


# ⬇️ USE YOUR FULL EntityTypeDetector HERE ⬇️
from kg_reorganizer import EntityTypeDetector  # or paste the class directly


# --------------------------------------------------
# KG PARSING
# --------------------------------------------------

def parse_kg(file_path: str) -> List[Tuple[str, str, str]]:
    triples = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            s, r, o = [x.strip() for x in line.split("|")]
            triples.append((s, r, o))
    return triples


# --------------------------------------------------
# SCHEMA EXTRACTION
# --------------------------------------------------

def extract_schema(triples, detector):
    node_type_freq = defaultdict(int)
    arc_freq = defaultdict(int)
    typed_arc_freq = defaultdict(int)

    # Collect context for better typing
    usage = defaultdict(lambda: {"as_subject": [], "as_object": []})
    for s, r, o in triples:
        usage[s]["as_subject"].append(r)
        usage[o]["as_object"].append(r)

    for s, r, o in triples:
        s_ctx = f"subject with relationships: {', '.join(usage[s]['as_subject'])}"
        o_ctx = r

        s_type = detector.detect_type(s, context=s_ctx)
        o_type = detector.detect_type(o, context=o_ctx)

        node_type_freq[s_type.value] += 1
        node_type_freq[o_type.value] += 1
        arc_freq[r] += 1

        key = (s_type.value, r, o_type.value)
        typed_arc_freq[key] += 1

    return node_type_freq, arc_freq, typed_arc_freq


# --------------------------------------------------
# SAVE RESULTS
# --------------------------------------------------

def save_arc_types(path, arc_freq):
    with open(path, "w", encoding="utf-8") as f:
        f.write("RELATIONSHIP|FREQUENCY\n")
        for r, c in sorted(arc_freq.items(), key=lambda x: -x[1]):
            f.write(f"{r}|{c}\n")


def save_node_types(path, node_type_freq):
    with open(path, "w", encoding="utf-8") as f:
        f.write("NODE_TYPE|FREQUENCY\n")
        for t, c in sorted(node_type_freq.items(), key=lambda x: -x[1]):
            f.write(f"{t}|{c}\n")


def save_typed_arcs(path, typed_arc_freq):
    with open(path, "w", encoding="utf-8") as f:
        f.write("SUBJECT_TYPE|RELATIONSHIP|OBJECT_TYPE|FREQUENCY\n")
        for (s_type, r, o_type), c in sorted(
            typed_arc_freq.items(), key=lambda x: -x[1]
        ):
            f.write(f"{s_type}|{r}|{o_type}|{c}\n")


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Extract KG schema statistics")
    parser.add_argument("input_file", help="KG file (subject|relation|object)")
    parser.add_argument("--out-prefix", default="kg_schema",
                        help="Output file prefix")

    args = parser.parse_args()

    config = ReorganizationConfig()
    detector = EntityTypeDetector(config)

    triples = parse_kg(args.input_file)

    node_type_freq, arc_freq, typed_arc_freq = extract_schema(triples, detector)

    save_arc_types(f"{args.out_prefix}_arc_types.txt", arc_freq)
    save_node_types(f"{args.out_prefix}_node_types.txt", node_type_freq)
    save_typed_arcs(f"{args.out_prefix}_typed_arcs.txt", typed_arc_freq)

    print("Schema extraction complete:")
    print(f"  Arc types:      {len(arc_freq)}")
    print(f"  Node types:     {len(node_type_freq)}")
    print(f"  Typed patterns: {len(typed_arc_freq)}")


if __name__ == "__main__":
    main()