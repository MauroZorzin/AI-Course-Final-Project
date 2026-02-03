#!/usr/bin/env python3
"""make_templates.py

Generate K query templates per hop length (1..3) from a MetaQA-style KB graph.

A "template" is primarily a RELATION CHAIN of length = hop (e.g., [r1, r2]),
plus a canonical natural-language question pattern with a {subj} placeholder.

Input KB format: one triple per line:
  head|relation|tail
or tab-separated (auto-detected).

Output: JSONL, one template per line, with fields:
  - template_id
  - hop
  - rel_chain
  - question_template          (contains {subj} placeholder)
  - query_plan_template        (symbolic plan, useful for prompting/eval)
  - provenance

Typical usage:
  python make_templates.py \
    --graph_path sources/graphs/natural.kb \
    --out_path sources/queries/natural_templates.jsonl \
    --templates_per_hop 20 --seed 42

Notes:
- If you rename relations in your abstract graph, either:
  (a) do NOT rename relations (recommended), or
  (b) re-run this on that graph variant to generate matching templates.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

Triple = Tuple[str, str, str]


def detect_delimiter(sample_line: str, user_delim: Optional[str] = None) -> str:
    if user_delim:
        return user_delim
    for d in ("|", "\t", ","):
        if len(sample_line.rstrip("\n").split(d)) == 3:
            return d
    raise ValueError("Could not auto-detect delimiter. Provide --delimiter.")


def read_triples(path: str, delimiter: Optional[str] = None) -> Tuple[List[Triple], str]:
    triples: List[Triple] = []
    with open(path, "r", encoding="utf-8") as f:
        first = None
        for line in f:
            if line.strip():
                first = line
                break
        if first is None:
            raise ValueError(f"Empty KB file: {path}")
        delim = detect_delimiter(first, delimiter)

        def parse_line(ln: str) -> Triple:
            parts = [p.strip() for p in ln.rstrip("\n").split(delim)]
            if len(parts) != 3:
                raise ValueError(f"Malformed triple line: {ln!r}")
            return (parts[0], parts[1], parts[2])

        triples.append(parse_line(first))
        for line in f:
            if not line.strip():
                continue
            triples.append(parse_line(line))
    return triples, delim


def build_adjacency(triples: Sequence[Triple]) -> Dict[str, List[Tuple[str, str]]]:
    adj: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    for h, r, t in triples:
        adj[h].append((r, t))
    return adj


def canonical_question_template(rel_chain: Sequence[str]) -> str:
    # Minimal and unambiguous; relation strings are inserted verbatim.
    if len(rel_chain) == 1:
        return "What is the {r1} of {subj}?"
    if len(rel_chain) == 2:
        return "What is the {r2} of the {r1} of {subj}?"
    if len(rel_chain) == 3:
        return "What is the {r3} of the {r2} of the {r1} of {subj}?"
    raise ValueError("Unsupported hop length.")


def canonical_plan_template(rel_chain: Sequence[str]) -> str:
    parts = ["subj"]
    for i, r in enumerate(rel_chain, start=1):
        var = "ans" if i == len(rel_chain) else f"x{i}"
        parts.append(f"--{r}--> {var}")
    return " ".join(parts)


def sample_relation_chains_random_walk(
    adj: Dict[str, List[Tuple[str, str]]],
    hop: int,
    k: int,
    rng: random.Random,
    max_attempts: int,
) -> List[List[str]]:
    nodes = list(adj.keys())
    if not nodes:
        raise ValueError("Graph has no heads (empty adjacency).")

    chains: List[List[str]] = []
    seen: Set[Tuple[str, ...]] = set()
    attempts = 0

    while len(chains) < k and attempts < max_attempts:
        attempts += 1
        cur = rng.choice(nodes)
        rels: List[str] = []
        ok = True
        for _ in range(hop):
            edges = adj.get(cur, [])
            if not edges:
                ok = False
                break
            r, nxt = rng.choice(edges)
            rels.append(r)
            cur = nxt
        if not ok:
            continue
        key = tuple(rels)
        if key in seen:
            continue
        seen.add(key)
        chains.append(rels)

    return chains


def normalize_out_path(user_out_path: str) -> Path:
    """If the user passes a directory, write <dir>/templates.jsonl.
    If the user passes a path with no suffix, append .jsonl.
    """
    p = Path(user_out_path)
    if p.exists() and p.is_dir():
        return p / "templates.jsonl"
    if p.suffix == "":
        return p.with_suffix(".jsonl")
    return p


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--graph_path", required=True, help="KB triples file (e.g., natural.kb).")
    ap.add_argument("--out_path", required=True, help="Output path (file or directory).")
    ap.add_argument("--delimiter", default=None, help="Delimiter for KB; auto-detect if omitted.")
    ap.add_argument("--seed", type=int, default=42, help="Sampling seed.")
    ap.add_argument("--hop_min", type=int, default=1, choices=[1, 2, 3])
    ap.add_argument("--hop_max", type=int, default=3, choices=[1, 2, 3])
    ap.add_argument("--templates_per_hop", type=int, default=20, help="K templates per hop.")
    ap.add_argument("--max_attempts", type=int, default=250000, help="Max sampling attempts per hop.")
    args = ap.parse_args()

    if args.hop_min > args.hop_max:
        raise ValueError("--hop_min must be <= --hop_max.")

    triples, _delim = read_triples(args.graph_path, args.delimiter)
    adj = build_adjacency(triples)

    relations = sorted({r for _, r, _ in triples})

    rng = random.Random(args.seed)

    out_path = normalize_out_path(args.out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    out: List[dict] = []
    for hop in range(args.hop_min, args.hop_max + 1):
        if hop == 1:
            # For hop=1, the maximum number of unique chains is the number of unique relations.
            chains_all = [[r] for r in relations]
            rng.shuffle(chains_all)
            chains = chains_all[: args.templates_per_hop]
            if len(chains) < args.templates_per_hop:
                print(f"[WARN] hop=1: requested {args.templates_per_hop}, got {len(chains)} unique chains (unique relations={len(relations)}).")
        else:
            chains = sample_relation_chains_random_walk(
                adj=adj,
                hop=hop,
                k=args.templates_per_hop,
                rng=rng,
                max_attempts=args.max_attempts,
            )
            if len(chains) < args.templates_per_hop:
                print(f"[WARN] hop={hop}: requested {args.templates_per_hop}, got {len(chains)} unique chains.")

        for j, chain in enumerate(chains, start=1):
            rel_slots = {f"r{i+1}": chain[i] for i in range(len(chain))}
            # Keep the {subj} placeholder intact while filling r1/r2/r3.
            rel_slots["subj"] = "{subj}"
            qtmpl = canonical_question_template(chain).format(**rel_slots)
            plan = canonical_plan_template(chain)
            template = {
                "template_id": f"H{hop}_T{j:04d}",
                "hop": hop,
                "rel_chain": chain,
                "question_template": qtmpl,
                "query_plan_template": plan,
                "provenance": {
                    "graph_path": args.graph_path,
                    "seed": args.seed,
                    "sampling": "relations" if hop == 1 else "random_walk",
                },
            }
            out.append(template)

    with open(out_path, "w", encoding="utf-8") as f:
        for obj in out:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    print(json.dumps({
        "graph_path": args.graph_path,
        "out_path": str(out_path),
        "seed": args.seed,
        "hop_min": args.hop_min,
        "hop_max": args.hop_max,
        "templates_per_hop": args.templates_per_hop,
        "num_templates_written": len(out),
        "unique_relations": len(relations),
    }, indent=2))


if __name__ == "__main__":
    main()
