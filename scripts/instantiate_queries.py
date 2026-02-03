#!/usr/bin/env python3
"""
instantiate_queries.py

Instantiate concrete query instances from:
  - a graph (or graphs_dir containing natural/abstract/counterfactual),
  - a templates JSONL (from make_templates.py).

Each instance includes:
  - hop, template_id, rel_chain
  - start_entity
  - question_text (template filled)
  - gold_answers (list) and gold_answer (first)
  - gold_path (one canonical path as list of triples)

This supports:
  - Hop lengths 1..3 fileciteturn1file0
  - Graph variants: natural/abstract/counterfactual fileciteturn1file0
  - Standardized templates across prompting strategies fileciteturn1file0

Output is JSONL; later steps can add evidence subgraphs (extract_subgraphs.py) and render prompts.

Typical usage:
  python instantiate_queries.py \
    --graphs_dir data/graphs \
    --templates_path data/templates.jsonl \
    --out_path data/queries.jsonl \
    --instances_per_template 20 \
    --seed 42 \
    --graph_variants natural abstract counterfactual \
    --single_answer_only

Paired natural/counterfactual mode (for override-rate analysis):
  python instantiate_queries.py ... --pair_natural_counterfactual

This emits:
  - natural instances
  - counterfactual instances with the SAME intent_key (same start_entity + rel_chain),
    and also includes natural_gold_answers for convenience.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

Triple = Tuple[str, str, str]


def detect_delimiter(sample_line: str, user_delim: Optional[str] = None) -> str:
    if user_delim:
        return user_delim
    for d in ["|", "\t", ","]:
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


def build_indexes(triples: Sequence[Triple]) -> Tuple[
    Dict[Tuple[str, str], List[str]],
    Dict[Tuple[str, str], List[str]],
    Set[str],
]:
    """
    hr_to_tails: (head, rel) -> [tail]
    rt_to_heads: (rel, tail) -> [head]  (for reverse DP)
    nodes: all entities
    """
    hr_to_tails: Dict[Tuple[str, str], List[str]] = defaultdict(list)
    rt_to_heads: Dict[Tuple[str, str], List[str]] = defaultdict(list)
    nodes: Set[str] = set()
    for h, r, t in triples:
        hr_to_tails[(h, r)].append(t)
        rt_to_heads[(r, t)].append(h)
        nodes.add(h); nodes.add(t)
    return hr_to_tails, rt_to_heads, nodes


def load_templates(path: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            if "template_id" not in obj or "hop" not in obj or "rel_chain" not in obj or "question_template" not in obj:
                raise ValueError(f"Template missing required fields: {obj}")
            out.append(obj)
    return out


def render_question(question_template: str, subj: str, rel_chain: Sequence[str]) -> str:
    # question_template already contains relation strings and {subj} placeholder only.
    return question_template.replace("{subj}", subj)


def sha1_id(*parts: str, prefix: str = "q") -> str:
    h = hashlib.sha1("||".join(parts).encode("utf-8")).hexdigest()
    return f"{prefix}_{h[:16]}"


def compute_valid_suffix_sets(
    rel_chain: Sequence[str],
    rt_to_heads: Dict[Tuple[str, str], List[str]],
    hr_to_tails: Dict[Tuple[str, str], List[str]],
) -> List[Set[str]]:
    """
    valid[i] = set of nodes that can start the suffix rel_chain[i:] and reach some endpoint.
    valid[len(chain)] = all nodes reachable as endpoints? Not needed; we define valid at positions 0..len(chain).
    We'll set valid[len(chain)] = set of all nodes (so last edge selection doesn't need constraint),
    but for reconstruction we want constraints for intermediate steps.

    We compute backwards:
      valid_last (position hop-1, before last rel) = heads that have an outgoing edge with last relation.
      Then valid at i = heads h such that exists tail x in valid[i+1] with (h, rel_i, x).
    """
    hop = len(rel_chain)
    # valid list length hop+1
    valid: List[Set[str]] = [set() for _ in range(hop + 1)]
    # For convenience, valid at hop = "any node"
    # (used only for last step checks; not restrictive)
    valid[hop] = set()

    # Initialize valid[hop-1]
    last_r = rel_chain[-1]
    heads = set()
    # heads that have any (h, last_r, t)
    for (h, r), tails in hr_to_tails.items():
        if r == last_r and tails:
            heads.add(h)
    valid[hop - 1] = heads

    # Backward DP
    for i in range(hop - 2, -1, -1):
        r = rel_chain[i]
        s: Set[str] = set()
        # For each node x that can start suffix from i+1, add heads h with (h, r, x)
        for x in valid[i + 1]:
            for h in rt_to_heads.get((r, x), []):
                s.add(h)
        valid[i] = s

    return valid


def follow_chain_collect_answers(
    start: str,
    rel_chain: Sequence[str],
    hr_to_tails: Dict[Tuple[str, str], List[str]],
) -> Set[str]:
    cur: Set[str] = {start}
    for r in rel_chain:
        nxt: Set[str] = set()
        for u in cur:
            for t in hr_to_tails.get((u, r), []):
                nxt.add(t)
        cur = nxt
        if not cur:
            break
    return cur


def pick_one_canonical_path(
    start: str,
    rel_chain: Sequence[str],
    hr_to_tails: Dict[Tuple[str, str], List[str]],
    valid_suffix: Optional[List[Set[str]]] = None,
) -> Optional[List[Triple]]:
    """
    Pick one path deterministically (lexicographic among possible tails),
    optionally constrained by valid_suffix sets to ensure completion.
    """
    path: List[Triple] = []
    cur = start
    hop = len(rel_chain)

    for i, r in enumerate(rel_chain):
        tails = hr_to_tails.get((cur, r), [])
        if not tails:
            return None

        candidates = sorted(set(tails))
        chosen = None
        for t in candidates:
            if i < hop - 1 and valid_suffix is not None:
                if t not in valid_suffix[i + 1]:
                    continue
            chosen = t
            break
        if chosen is None:
            # no candidate can complete the remaining suffix
            return None
        path.append((cur, r, chosen))
        cur = chosen
    return path


def instantiate_for_graph(
    graph_variant: str,
    graph_path: str,
    templates: Sequence[Dict[str, Any]],
    instances_per_template: int,
    seed: int,
    delimiter: Optional[str],
    single_answer_only: bool,
    max_attempts_per_template: int = 500000,
) -> List[Dict[str, Any]]:
    triples, _delim = read_triples(graph_path, delimiter)
    hr_to_tails, rt_to_heads, nodes = build_indexes(triples)

    rng = random.Random(seed + (abs(hash(graph_variant)) % 10_000))

    out: List[Dict[str, Any]] = []

    for tmpl in templates:
        hop = int(tmpl["hop"])
        rel_chain = list(tmpl["rel_chain"])
        question_template = str(tmpl["question_template"])
        template_id = str(tmpl["template_id"])

        # Compute valid starts to avoid heavy rejection sampling
        valid_suffix = compute_valid_suffix_sets(rel_chain, rt_to_heads, hr_to_tails)
        start_candidates = sorted(valid_suffix[0])

        if not start_candidates:
            print(f"[WARN] graph={graph_variant} template={template_id}: no valid starts; skipping.")
            continue

        # Sample starts without replacement if possible; else with replacement
        # To keep reproducible, shuffle once and iterate.
        rng.shuffle(start_candidates)

        produced = 0
        idx = 0
        attempts = 0

        while produced < instances_per_template and attempts < max_attempts_per_template:
            attempts += 1
            if idx >= len(start_candidates):
                # wrap around (with replacement)
                idx = 0
                rng.shuffle(start_candidates)
            start = start_candidates[idx]
            idx += 1

            answers = follow_chain_collect_answers(start, rel_chain, hr_to_tails)
            if not answers:
                continue

            answers_sorted = sorted(answers)
            if single_answer_only and len(answers_sorted) != 1:
                continue

            gold_path = pick_one_canonical_path(start, rel_chain, hr_to_tails, valid_suffix=valid_suffix)
            if gold_path is None:
                continue

            intent_key = sha1_id(template_id, start, "|".join(rel_chain), prefix="intent")
            qid = sha1_id(graph_variant, intent_key, prefix="q")

            qtext = render_question(question_template, start, rel_chain)

            obj = {
                "id": qid,
                "intent_key": intent_key,   # stable across variants if start/chain identical
                "graph_variant": graph_variant,
                "graph_path": graph_path,
                "hop": hop,
                "template_id": template_id,
                "rel_chain": rel_chain,
                "start_entity": start,
                "question_text": qtext,
                "gold_answers": answers_sorted,
                "gold_answer": answers_sorted[0],
                "gold_path": [[h, r, t] for (h, r, t) in gold_path],
                "provenance": {
                    "seed": seed,
                    "single_answer_only": bool(single_answer_only),
                },
            }
            out.append(obj)
            produced += 1

        if produced < instances_per_template:
            print(f"[WARN] graph={graph_variant} template={template_id}: produced {produced}/{instances_per_template} after {attempts} attempts.")

    return out


def load_graph_paths(graphs_dir: str, variants: Sequence[str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for v in variants:
        cand = os.path.join(graphs_dir, f"{v}.kb")
        if not os.path.exists(cand):
            raise FileNotFoundError(f"Missing graph file for variant '{v}': {cand}")
        out[v] = cand
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--graphs_dir", help="Directory containing <variant>.kb files (e.g., natural.kb).")
    g.add_argument("--graph_path", help="Single graph path; use with --graph_variant_name.")
    ap.add_argument("--graph_variant_name", default="graph", help="Variant name when using --graph_path.")
    ap.add_argument("--templates_path", required=True, help="Templates JSONL from make_templates.py.")
    ap.add_argument("--out_path", required=True, help="Output JSONL query instances.")
    ap.add_argument("--delimiter", default=None, help="Delimiter for KB; auto-detect if omitted.")
    ap.add_argument("--seed", type=int, default=42, help="Seed for sampling.")
    ap.add_argument("--instances_per_template", type=int, default=20, help="How many instances per template per graph.")
    ap.add_argument("--graph_variants", nargs="*", default=["natural", "abstract", "counterfactual"],
                    help="Graph variants to instantiate (requires --graphs_dir).")
    ap.add_argument("--single_answer_only", action="store_true",
                    help="Keep only instances with exactly one gold answer (simplifies EM/F1).")
    ap.add_argument("--pair_natural_counterfactual", action="store_true",
                    help="Instantiate natural first, then counterfactual using same intent_key (start+chain).")
    args = ap.parse_args()

    templates = load_templates(args.templates_path)

    all_instances: List[Dict[str, Any]] = []

    if args.graph_path:
        instances = instantiate_for_graph(
            graph_variant=args.graph_variant_name,
            graph_path=args.graph_path,
            templates=templates,
            instances_per_template=args.instances_per_template,
            seed=args.seed,
            delimiter=args.delimiter,
            single_answer_only=args.single_answer_only,
        )
        all_instances.extend(instances)

    else:
        # graphs_dir mode
        if args.pair_natural_counterfactual:
            # Force order and require both
            variants = list(args.graph_variants)
            if "natural" not in variants or "counterfactual" not in variants:
                raise ValueError("--pair_natural_counterfactual requires both 'natural' and 'counterfactual' in --graph_variants.")
            graph_paths = load_graph_paths(args.graphs_dir, variants)

            # 1) instantiate natural
            natural_instances = instantiate_for_graph(
                graph_variant="natural",
                graph_path=graph_paths["natural"],
                templates=templates,
                instances_per_template=args.instances_per_template,
                seed=args.seed,
                delimiter=args.delimiter,
                single_answer_only=args.single_answer_only,
            )
            # index by intent_key
            natural_by_intent = {q["intent_key"]: q for q in natural_instances}
            all_instances.extend(natural_instances)

            # 2) instantiate counterfactual for SAME intents
            # We'll create counterfactual instances by re-evaluating the same start+chain on counterfactual graph.
            # If no answer/path exists, skip that intent.
            cf_triples, _ = read_triples(graph_paths["counterfactual"], args.delimiter)
            hr_to_tails, rt_to_heads, _nodes = build_indexes(cf_triples)

            kept_cf = 0
            for intent_key, nq in natural_by_intent.items():
                start = nq["start_entity"]
                rel_chain = nq["rel_chain"]
                hop = nq["hop"]
                template_id = nq["template_id"]
                qtmpl = None
                # find template's question_template
                # (small templates list, linear scan ok)
                for t in templates:
                    if t["template_id"] == template_id:
                        qtmpl = t["question_template"]
                        break
                if qtmpl is None:
                    continue

                answers = follow_chain_collect_answers(start, rel_chain, hr_to_tails)
                if not answers:
                    continue
                answers_sorted = sorted(answers)
                if args.single_answer_only and len(answers_sorted) != 1:
                    continue

                valid_suffix = compute_valid_suffix_sets(rel_chain, rt_to_heads, hr_to_tails)
                gold_path = pick_one_canonical_path(start, rel_chain, hr_to_tails, valid_suffix=valid_suffix)
                if gold_path is None:
                    continue

                qid = sha1_id("counterfactual", intent_key, prefix="q")
                qtext = qtmpl.replace("{subj}", start)

                obj = {
                    "id": qid,
                    "intent_key": intent_key,
                    "graph_variant": "counterfactual",
                    "graph_path": graph_paths["counterfactual"],
                    "hop": hop,
                    "template_id": template_id,
                    "rel_chain": rel_chain,
                    "start_entity": start,
                    "question_text": qtext,
                    "gold_answers": answers_sorted,
                    "gold_answer": answers_sorted[0],
                    "gold_path": [[h, r, t] for (h, r, t) in gold_path],
                    "natural_gold_answers": nq["gold_answers"],
                    "natural_gold_answer": nq["gold_answer"],
                    "provenance": {
                        "seed": args.seed,
                        "single_answer_only": bool(args.single_answer_only),
                        "paired_with_natural": True,
                    },
                }
                all_instances.append(obj)
                kept_cf += 1

            # 3) instantiate any remaining variants independently (e.g., abstract)
            for v in variants:
                if v in ("natural", "counterfactual"):
                    continue
                instances = instantiate_for_graph(
                    graph_variant=v,
                    graph_path=graph_paths[v],
                    templates=templates,
                    instances_per_template=args.instances_per_template,
                    seed=args.seed,
                    delimiter=args.delimiter,
                    single_answer_only=args.single_answer_only,
                )
                all_instances.extend(instances)

            print(f"[INFO] paired counterfactual instances kept: {kept_cf}/{len(natural_by_intent)}")

        else:
            graph_paths = load_graph_paths(args.graphs_dir, args.graph_variants)
            for v in args.graph_variants:
                instances = instantiate_for_graph(
                    graph_variant=v,
                    graph_path=graph_paths[v],
                    templates=templates,
                    instances_per_template=args.instances_per_template,
                    seed=args.seed,
                    delimiter=args.delimiter,
                    single_answer_only=args.single_answer_only,
                )
                all_instances.extend(instances)

    # Write JSONL
    os.makedirs(os.path.dirname(args.out_path) or ".", exist_ok=True)
    with open(args.out_path, "w", encoding="utf-8") as f:
        for obj in all_instances:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    # Summary
    by_variant = defaultdict(int)
    by_hop = defaultdict(int)
    for q in all_instances:
        by_variant[q["graph_variant"]] += 1
        by_hop[int(q["hop"])] += 1

    print(json.dumps({
        "out_path": args.out_path,
        "seed": args.seed,
        "instances_per_template": args.instances_per_template,
        "single_answer_only": bool(args.single_answer_only),
        "pair_natural_counterfactual": bool(args.pair_natural_counterfactual),
        "num_instances_written": len(all_instances),
        "by_variant": dict(by_variant),
        "by_hop": dict(by_hop),
    }, indent=2))


if __name__ == "__main__":
    main()
