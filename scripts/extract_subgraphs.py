#!/usr/bin/env python3
"""
extract_subgraphs.py

Given a graph (KB triples) and a set of query instances, build minimal "evidence subgraphs"
to support lowest-context prompting while preserving comparability across models/strategies.

Intended query input format: JSONL, one object per line. Required fields:
  - id: string/int
  - hop: int (1..3)
And EITHER:
  A) gold_path: list of triples, each triple as [head, relation, tail] (preferred)
OR
  B) start_entity, answer, hop: script will attempt to find a path of length hop via BFS.
     Note: BFS may find an arbitrary path if multiple exist.

Output: JSONL, same objects plus:
  - evidence_triples: list of triples as [head, relation, tail]
  - evidence_stats: {num_evidence, num_gold, num_distractors, additional_triples}

Distractor policy (modified):
  - For each gold triple (h, r, t), add K distractors of form (h', r, t') where (h', r, t') != (h, r, t).
  - If strategy distractors are insufficient to fill max_triples, add random triples from the KB.

Example:
  python extract_subgraphs.py \
    --graph_path data/graphs/natural.kb \
    --queries_path data/queries.jsonl \
    --out_path data/queries_with_evidence.jsonl \
    --distractors_per_hop 2 --max_triples 12 --seed 42
"""
from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict, deque
from typing import Any, Deque, Dict, Iterable, List, Optional, Sequence, Set, Tuple


Triple = Tuple[str, str, str]


def detect_delimiter(sample_line: str, user_delim: Optional[str] = None) -> str:
    if user_delim:
        return user_delim
    candidates = ["|", "\t", ","]
    for d in candidates:
        parts = sample_line.rstrip("\n").split(d)
        if len(parts) == 3:
            return d
    raise ValueError("Could not auto-detect delimiter. Provide --delimiter.")


def read_triples(path: str, delimiter: Optional[str] = None) -> Tuple[List[Triple], str]:
    triples: List[Triple] = []
    with open(path, "r", encoding="utf-8") as f:
        first_nonempty = None
        for line in f:
            if line.strip():
                first_nonempty = line
                break
        if first_nonempty is None:
            raise ValueError(f"Empty KB file: {path}")
        delim = detect_delimiter(first_nonempty, delimiter)

        def parse_line(ln: str) -> Triple:
            parts = [p.strip() for p in ln.rstrip("\n").split(delim)]
            if len(parts) != 3:
                raise ValueError(f"Malformed triple line: {ln!r}")
            return (parts[0], parts[1], parts[2])

        triples.append(parse_line(first_nonempty))
        for line in f:
            if not line.strip():
                continue
            triples.append(parse_line(line))
    return triples, delim


def build_index(triples: Sequence[Triple]) -> Tuple[Dict[str, List[Tuple[str, str]]], Dict[Tuple[str, str], List[str]], Dict[str, List[Triple]]]:
    """
    adjacency: head -> list of (relation, tail)
    hr_to_tails: (head, relation) -> list of tails
    r_to_triples: relation -> list of triples
    """
    adjacency: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    hr_to_tails: Dict[Tuple[str, str], List[str]] = defaultdict(list)
    r_to_triples: Dict[str, List[Triple]] = defaultdict(list)
    for h, r, t in triples:
        adjacency[h].append((r, t))
        hr_to_tails[(h, r)].append(t)
        r_to_triples[r].append((h, r, t))
    return adjacency, hr_to_tails, r_to_triples


def parse_gold_path(obj: Dict[str, Any]) -> Optional[List[Triple]]:
    gp = obj.get("gold_path", None)
    if gp is None:
        gp = obj.get("path_triples", None)
    if gp is None:
        return None
    out: List[Triple] = []
    for tri in gp:
        if isinstance(tri, (list, tuple)) and len(tri) == 3:
            out.append((str(tri[0]), str(tri[1]), str(tri[2])))
        elif isinstance(tri, str):
            # allow "h|r|t" strings
            parts = tri.split("|")
            if len(parts) != 3:
                raise ValueError(f"Cannot parse gold_path triple string: {tri!r}")
            out.append((parts[0].strip(), parts[1].strip(), parts[2].strip()))
        else:
            raise ValueError(f"Unsupported gold_path triple format: {tri!r}")
    return out


def bfs_find_path(
    start: str,
    target: str,
    hop: int,
    adjacency: Dict[str, List[Tuple[str, str]]],
) -> Optional[List[Triple]]:
    """
    BFS over paths up to exactly `hop` edges; returns first found exact-length path.
    """
    if hop <= 0:
        return None

    # state: (node, depth)
    q: Deque[Tuple[str, int]] = deque()
    q.append((start, 0))
    # predecessor: (node, depth) -> (prev_node, prev_depth, relation)
    pred: Dict[Tuple[str, int], Tuple[str, int, str]] = {}

    visited: Set[Tuple[str, int]] = set()
    visited.add((start, 0))

    while q:
        node, depth = q.popleft()
        if depth == hop:
            continue
        for rel, nxt in adjacency.get(node, []):
            nd = depth + 1
            st = (nxt, nd)
            if st in visited:
                continue
            visited.add(st)
            pred[st] = (node, depth, rel)
            # stop if we reached target at exact hop
            if nxt == target and nd == hop:
                # reconstruct
                path_nodes = (nxt, nd)
                triples: List[Triple] = []
                cur_node, cur_depth = nxt, nd
                while cur_depth > 0:
                    prev_node, prev_depth, rel_used = pred[(cur_node, cur_depth)]
                    triples.append((prev_node, rel_used, cur_node))
                    cur_node, cur_depth = prev_node, prev_depth
                triples.reverse()
                return triples
            q.append((nxt, nd))
    return None


def sample_distractors_by_relation(
    r: str,
    gold_triple: Triple,
    r_to_triples: Dict[str, List[Triple]],
    rng: random.Random,
    k: int,
    avoid_tails: Optional[Set[str]] = None,
) -> List[Triple]:
    candidates = r_to_triples.get(r, [])
    # Filter out the gold triple itself
    if avoid_tails:
        valid = [c for c in candidates if c != gold_triple and c[2] not in avoid_tails]
    else:
        valid = [c for c in candidates if c != gold_triple]
    if not valid or k <= 0:
        return []
    if len(valid) <= k:
        return valid
    return rng.sample(valid, k)


def build_evidence_for_query(
    gold_path: List[Triple],
    r_to_triples: Dict[str, List[Triple]],
    all_triples: List[Triple],
    rng: random.Random,
    distractors_per_hop: int,
    max_triples: int,
    avoid_tails: Optional[Set[str]] = None,
) -> Tuple[List[Triple], Dict[str, int]]:
    """
    Evidence = gold path triples + distractors.
    Strategy:
      1. Gold path (always included).
      2. Relation-based distractors: For each gold triple (h, r, t), find k triples (h', r, t') != (h, r, t).
      3. Additional random triples: If budget permits, fill with random facts from KB.
    """
    evidence_list: List[Triple] = list(gold_path)
    evidence_set: Set[Triple] = set(gold_path)
    
    # 1. Relation-based distractors
    rel_distractors: List[Triple] = []
    for (h, r, t) in gold_path:
        sample = sample_distractors_by_relation(
            r=r,
            gold_triple=(h, r, t),
            r_to_triples=r_to_triples,
            rng=rng,
            k=distractors_per_hop,
            avoid_tails=avoid_tails,
        )
        rel_distractors.extend(sample)

    # Add unique relation distractors, adhering to max_triples
    count_rel_distractors = 0
    for tri in rel_distractors:
        if len(evidence_list) >= max_triples:
            break
        if tri not in evidence_set:
            evidence_set.add(tri)
            evidence_list.append(tri)
            count_rel_distractors += 1

    # 2. Additional random triples
    # Fill remaining spots with random triples from KB
    count_additional = 0
    needed = max_triples - len(evidence_list)
    
    if needed > 0 and all_triples:
        # Try to sample efficiently. 
        # If needed is small relative to len(all_triples), rejection sampling is fine.
        # Limit attempts to avoid infinite loops if graph is small/saturated.
        attempts = 0
        max_attempts = needed * 5 + 100
        while len(evidence_list) < max_triples and attempts < max_attempts:
            attempts += 1
            cand = rng.choice(all_triples)
            if cand not in evidence_set:
                if avoid_tails and cand[2] in avoid_tails:
                    continue
                evidence_set.add(cand)
                evidence_list.append(cand)
                count_additional += 1

    stats = {
        "num_evidence": len(evidence_list),
        "num_gold": len(gold_path),
        "num_distractors": count_rel_distractors,
        "additional_triples": count_additional
    }
    return evidence_list, stats


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--graph_path", required=True, help="KB triples file for a specific graph variant.")
    ap.add_argument("--queries_path", required=True, help="Input JSONL queries.")
    ap.add_argument("--out_path", required=True, help="Output JSONL with evidence_triples added.")
    ap.add_argument("--delimiter", default=None, help="Delimiter for KB file. If omitted, auto-detect.")
    ap.add_argument("--seed", type=int, default=42, help="Seed for distractor sampling.")
    ap.add_argument("--distractors_per_hop", type=int, default=20, help="Local distractors per gold hop.")
    ap.add_argument("--max_triples", type=int, default=100, help="Max evidence triples per query (keeps gold).")
    ap.add_argument("--require_gold_path", action="store_true", help="If set, fail when gold_path is missing (no BFS fallback).")
    args = ap.parse_args()

    rng = random.Random(args.seed)

    triples, _delim = read_triples(args.graph_path, args.delimiter)
    # Build updated index
    adjacency, hr_to_tails, r_to_triples = build_index(triples)

    num_in = 0
    num_out = 0
    num_missing_path = 0

    with open(args.queries_path, "r", encoding="utf-8") as fin, open(args.out_path, "w", encoding="utf-8") as fout:
        for line in fin:
            if not line.strip():
                continue
            num_in += 1
            obj = json.loads(line)

            hop = int(obj.get("hop", obj.get("hop_length", 0)))
            if hop <= 0:
                raise ValueError(f"Query missing valid hop: {obj.get('id', num_in)}")

            gold_path = parse_gold_path(obj)
            if gold_path is None and not args.require_gold_path:
                start = obj.get("start_entity") or obj.get("subject") or obj.get("head")
                ans = obj.get("answer") or obj.get("gold_answer")
                if start is not None and ans is not None:
                    gold_path = bfs_find_path(str(start), str(ans), hop, adjacency)
            if gold_path is None:
                num_missing_path += 1
                if args.require_gold_path:
                    raise ValueError(f"Missing gold_path for query id={obj.get('id')}")
                # Still emit with empty evidence to keep alignment, but mark it.
                obj["evidence_triples"] = []
                obj["evidence_stats"] = {"num_evidence": 0, "num_gold": 0, "num_distractors": 0, "additional_triples": 0, "missing_gold_path": 1}
                fout.write(json.dumps(obj, ensure_ascii=False) + "\n")
                num_out += 1
                continue

            # Identify target answer from gold_path and other valid answers to avoid
            avoid_tails = set()
            gold_answers_raw = obj.get("gold_answers")
            if not gold_answers_raw:
                val = obj.get("answer") or obj.get("gold_answer")
                if val:
                    gold_answers_raw = [val] if not isinstance(val, list) else val
            
            if gold_answers_raw and gold_path:
                target_answer = gold_path[-1][2]
                all_answers = set(str(x) for x in gold_answers_raw)
                avoid_tails = all_answers - {target_answer}

            evidence, estats = build_evidence_for_query(
                gold_path=gold_path,
                r_to_triples=r_to_triples,
                all_triples=triples,
                rng=rng,
                distractors_per_hop=args.distractors_per_hop,
                max_triples=args.max_triples,
                avoid_tails=avoid_tails,
            )

            obj["gold_path"] = [[h, r, t] for (h, r, t) in gold_path]
            obj["evidence_triples"] = [[h, r, t] for (h, r, t) in evidence]
            obj["evidence_stats"] = estats

            fout.write(json.dumps(obj, ensure_ascii=False) + "\n")
            num_out += 1

    # Lightweight run summary (stdout)
    print(json.dumps({
        "graph_path": args.graph_path,
        "queries_path": args.queries_path,
        "out_path": args.out_path,
        "seed": args.seed,
        "distractors_per_hop": args.distractors_per_hop,
        "max_triples": args.max_triples,
        "num_in": num_in,
        "num_out": num_out,
        "num_missing_gold_path": num_missing_path,
    }, indent=2))



if __name__ == "__main__":
    main()
