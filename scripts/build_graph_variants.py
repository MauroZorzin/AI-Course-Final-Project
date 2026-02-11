#!/usr/bin/env python3
"""
build_graph_variants.py

Create MetaQA graph variants:
  - Natural (baseline): identical to input KB.
  - Abstract: renames entities (optionally relations) to remove semantic cues.
  - Counterfactual: keeps real names but corrupts facts to test context adherence.

Designed to support common MetaQA KB formats (one triple per line):
  head|relation|tail
or tab-separated.

Outputs:
  <out_dir>/
    natural.kb
    abstract.kb
    abstract_entity_map.json
    abstract_relation_map.json   (only if --rename-relations)
    counterfactual.kb
    counterfactual_edits.jsonl
    variant_stats.json

Example:
  python build_graph_variants.py --kb_path kb.txt --out_dir data/graphs --seed 42 \
    --counterfactual_ratio 1.0 --counterfactual_mode swap_tails_within_relation
"""
from __future__ import annotations

import argparse
import json
import os
import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple


Triple = Tuple[str, str, str]


def detect_delimiter(sample_line: str, user_delim: Optional[str] = None) -> str:
    if user_delim:
        return user_delim
    candidates = ["|", "\t", ","]
    best = None
    for d in candidates:
        parts = sample_line.rstrip("\n").split(d)
        if len(parts) == 3:
            best = d
            break
    if not best:
        raise ValueError(
            "Could not auto-detect delimiter. Provide --delimiter. "
            "Expected 3 fields per line."
        )
    return best


def read_triples(path: str, delimiter: Optional[str] = None) -> Tuple[List[Triple], str]:
    triples: List[Triple] = []
    with open(path, "r", encoding="utf-8") as f:
        # Find first non-empty line for delimiter detection
        first_nonempty = None
        for line in f:
            if line.strip():
                first_nonempty = line
                break
        if first_nonempty is None:
            raise ValueError(f"Empty KB file: {path}")

        delim = detect_delimiter(first_nonempty, delimiter)
        # parse the first line + rest
        def parse_line(ln: str) -> Triple:
            parts = [p.strip() for p in ln.rstrip("\n").split(delim)]
            if len(parts) != 3:
                raise ValueError(f"Malformed triple line (expected 3 fields): {ln!r}")
            return (parts[0], parts[1], parts[2])

        triples.append(parse_line(first_nonempty))
        for line in f:
            if not line.strip():
                continue
            triples.append(parse_line(line))

    return triples, delim


def write_triples(path: str, triples: Sequence[Triple], delimiter: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for h, r, t in triples:
            f.write(f"{h}{delimiter}{r}{delimiter}{t}\n")


def make_abstract_maps(
    triples: Sequence[Triple],
    seed: int,
    rename_relations: bool,
    entity_prefix: str = "E",
    relation_prefix: str = "R",
) -> Tuple[Dict[str, str], Dict[str, str]]:
    entities: Set[str] = set()
    relations: Set[str] = set()
    for h, r, t in triples:
        entities.add(h); entities.add(t)
        relations.add(r)

    rng = random.Random(seed)

    ent_list = list(entities)
    rng.shuffle(ent_list)
    ent_map = {e: f"{entity_prefix}{i:07d}" for i, e in enumerate(ent_list, start=1)}

    rel_map: Dict[str, str] = {}
    if rename_relations:
        rel_list = list(relations)
        rng.shuffle(rel_list)
        rel_map = {r: f"{relation_prefix}{i:05d}" for i, r in enumerate(rel_list, start=1)}

    return ent_map, rel_map


def apply_maps(triples: Sequence[Triple], ent_map: Dict[str, str], rel_map: Dict[str, str]) -> List[Triple]:
    out: List[Triple] = []
    for h, r, t in triples:
        nh = ent_map.get(h, h)
        nt = ent_map.get(t, t)
        nr = rel_map.get(r, r)
        out.append((nh, nr, nt))
    return out


@dataclass
class CounterfactualStats:
    requested_ratio: float
    changed: int
    attempted: int
    duplicates_avoided: int


def build_counterfactual(
    triples: Sequence[Triple],
    seed: int,
    ratio: float,
    mode: str,
    max_tries: int = 50,
) -> Tuple[List[Triple], List[dict], CounterfactualStats]:
    """
    Create counterfactual triples while keeping entity strings unchanged.

    Modes:
      - swap_tails_within_relation (default): within each relation, permute tails.
        Preserves relation distribution and roughly preserves tail frequency per relation.
      - random_tail_same_relation: replace tail with random entity, keeping (h,r) fixed.

    Corrupts approximately `ratio` fraction of triples (0..1).
    """
    if not (0.0 <= ratio <= 1.0):
        raise ValueError("--counterfactual_ratio must be in [0,1].")

    rng = random.Random(seed)

    entities: List[str] = sorted({x for tri in triples for x in (tri[0], tri[2])})
    ent_set = set(entities)
    if len(ent_set) < 3:
        raise ValueError("Need at least 3 entities to build meaningful counterfactuals.")

    triple_set: Set[Triple] = set(triples)

    by_rel: Dict[str, List[int]] = defaultdict(list)
    for i, (_, r, _) in enumerate(triples):
        by_rel[r].append(i)

    n_total = len(triples)
    n_target = int(round(n_total * ratio))

    # Choose which indices to corrupt
    all_idx = list(range(n_total))
    rng.shuffle(all_idx)
    corrupt_idx = set(all_idx[:n_target])

    out = list(triples)
    edits: List[dict] = []
    duplicates_avoided = 0
    attempted = 0
    changed = 0

    if mode == "swap_tails_within_relation":
        # For each relation, permute tails among the corrupt subset for that relation
        for r, idxs in by_rel.items():
            idxs_corrupt = [i for i in idxs if i in corrupt_idx]
            if len(idxs_corrupt) <= 1:
                continue
            tails = [triples[i][2] for i in idxs_corrupt]
            perm = tails[:]
            rng.shuffle(perm)

            # If shuffle accidentally keeps some tails in place, rotate until different or give up
            # We'll handle per-edge with fallback random sampling.
            for i, new_t in zip(idxs_corrupt, perm):
                old_h, old_r, old_t = out[i]
                if new_t == old_t:
                    attempted += 1
                    # fallback: random tail
                    for _ in range(max_tries):
                        # FIX: Sample from the tails of the current relation, NOT the global entities list
                        # to avoid type mismatches (e.g. swapping a year with a person).
                        cand = rng.choice(tails)
                        if cand != old_t:
                            new_t = cand
                            break

                attempted += 1
                # Avoid duplicates and identity
                if new_t == old_t:
                    continue

                new_tri = (old_h, old_r, new_t)
                if new_tri in triple_set:
                    # try to find alternative tail
                    found = False
                    for _ in range(max_tries):
                        cand = rng.choice(entities)
                        if cand == old_t:
                            continue
                        cand_tri = (old_h, old_r, cand)
                        if cand_tri not in triple_set:
                            new_tri = cand_tri
                            new_t = cand
                            found = True
                            break
                    if not found:
                        duplicates_avoided += 1
                        continue

                # Apply edit
                triple_set.discard((old_h, old_r, old_t))
                triple_set.add(new_tri)
                out[i] = new_tri
                edits.append({
                    "index": i,
                    "old": {"h": old_h, "r": old_r, "t": old_t},
                    "new": {"h": old_h, "r": old_r, "t": new_t},
                    "mode": mode,
                })
                changed += 1

    elif mode == "random_tail_same_relation":
        for i in sorted(corrupt_idx):
            old_h, old_r, old_t = out[i]
            attempted += 1
            # try random replacements
            new_tri = None
            for _ in range(max_tries):
                cand = rng.choice(entities)
                if cand == old_t:
                    continue
                cand_tri = (old_h, old_r, cand)
                if cand_tri not in triple_set:
                    new_tri = cand_tri
                    break
            if new_tri is None:
                duplicates_avoided += 1
                continue
            triple_set.discard((old_h, old_r, old_t))
            triple_set.add(new_tri)
            out[i] = new_tri
            edits.append({
                "index": i,
                "old": {"h": old_h, "r": old_r, "t": old_t},
                "new": {"h": new_tri[0], "r": new_tri[1], "t": new_tri[2]},
                "mode": mode,
            })
            changed += 1
    else:
        raise ValueError(f"Unknown --counterfactual_mode: {mode}")

    stats = CounterfactualStats(
        requested_ratio=ratio,
        changed=changed,
        attempted=attempted,
        duplicates_avoided=duplicates_avoided,
    )
    return out, edits, stats


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb_path", required=True, help="Path to KB triples file (MetaQA-style).")
    ap.add_argument("--out_dir", required=True, help="Output directory.")
    ap.add_argument("--delimiter", default=None, help="Field delimiter. If omitted, auto-detect.")
    ap.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility.")
    ap.add_argument("--rename_relations", action="store_true", help="Also abstract relation names.")
    ap.add_argument("--entity_prefix", default="E", help="Prefix for abstract entity IDs.")
    ap.add_argument("--relation_prefix", default="R", help="Prefix for abstract relation IDs.")
    ap.add_argument("--counterfactual_ratio", type=float, default=1.0,
                    help="Fraction of triples to corrupt for counterfactual graph (0..1).")
    ap.add_argument("--counterfactual_mode", default="swap_tails_within_relation",
                    choices=["swap_tails_within_relation", "random_tail_same_relation"],
                    help="How to corrupt facts for counterfactual graph.")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    triples, delim = read_triples(args.kb_path, args.delimiter)

    # Natural
    natural_path = os.path.join(args.out_dir, "natural.kb")
    write_triples(natural_path, triples, delim)

    # Abstract
    ent_map, rel_map = make_abstract_maps(
        triples=triples,
        seed=args.seed,
        rename_relations=args.rename_relations,
        entity_prefix=args.entity_prefix,
        relation_prefix=args.relation_prefix,
    )
    abstract_triples = apply_maps(triples, ent_map, rel_map)
    abstract_path = os.path.join(args.out_dir, "abstract.kb")
    write_triples(abstract_path, abstract_triples, delim)

    with open(os.path.join(args.out_dir, "abstract_entity_map.json"), "w", encoding="utf-8") as f:
        json.dump(ent_map, f, ensure_ascii=False, indent=2)
    if args.rename_relations:
        with open(os.path.join(args.out_dir, "abstract_relation_map.json"), "w", encoding="utf-8") as f:
            json.dump(rel_map, f, ensure_ascii=False, indent=2)

    # Counterfactual
    counter_triples, edits, cf_stats = build_counterfactual(
        triples=triples,
        seed=args.seed,
        ratio=args.counterfactual_ratio,
        mode=args.counterfactual_mode,
    )
    counter_path = os.path.join(args.out_dir, "counterfactual.kb")
    write_triples(counter_path, counter_triples, delim)

    edits_path = os.path.join(args.out_dir, "counterfactual_edits.jsonl")
    with open(edits_path, "w", encoding="utf-8") as f:
        for e in edits:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    # Stats
    entities = sorted({x for tri in triples for x in (tri[0], tri[2])})
    relations = sorted({tri[1] for tri in triples})
    stats = {
        "input_kb": args.kb_path,
        "delimiter": delim,
        "seed": args.seed,
        "num_triples": len(triples),
        "num_entities": len(entities),
        "num_relations": len(relations),
        "rename_relations": bool(args.rename_relations),
        "counterfactual": {
            "mode": args.counterfactual_mode,
            "requested_ratio": cf_stats.requested_ratio,
            "changed": cf_stats.changed,
            "changed_ratio": cf_stats.changed / max(1, len(triples)),
            "attempted": cf_stats.attempted,
            "duplicates_avoided": cf_stats.duplicates_avoided,
        },
        "outputs": {
            "natural": natural_path,
            "abstract": abstract_path,
            "counterfactual": counter_path,
            "entity_map": os.path.join(args.out_dir, "abstract_entity_map.json"),
            "relation_map": os.path.join(args.out_dir, "abstract_relation_map.json") if args.rename_relations else None,
            "counterfactual_edits": edits_path,
        },
    }
    with open(os.path.join(args.out_dir, "variant_stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
