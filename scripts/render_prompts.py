#!/usr/bin/env python3
"""
render_prompts.py

Render prompts from query instances (JSONL) for:
  - direct prompting
  - structured CoT (sCoT)

User requirement: direct prompting does NOT need to output the reasoning path.
This script therefore:
  - direct: asks only for {"final_answer": "..."}
  - sCoT: asks for {"reasoning": [...], "final_answer": "..."} (no explicit path)

Input JSONL is expected to come from instantiate_queries.py and (optionally) extract_subgraphs.py.
We use evidence triples when available:
  - evidence_triples (preferred)
  - fallback to gold_path if evidence_triples is missing

Output JSONL: one record per (query instance × prompting strategy), including a
`messages` array (system+user) suitable for most chat APIs.

Example:
  python render_prompts.py \
    --queries_path data/queries_with_evidence.jsonl \
    --out_path data/prompts.jsonl \
    --prompting_strategies direct scot \
    --max_evidence_triples 12 \
    --allow_unknown

Notes:
- Evidence is presented as triples (head | relation | tail). Models are instructed to
  use ONLY the provided facts and otherwise answer UNKNOWN.
- JSON-only output is enforced to simplify evaluation.
"""
from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple


def format_triples(triples: Sequence[Sequence[str]], sep: str = " | ") -> str:
    lines: List[str] = []
    for tri in triples:
        if not (isinstance(tri, (list, tuple)) and len(tri) == 3):
            raise ValueError(f"Malformed triple (expected 3 items): {tri!r}")
        h, r, t = str(tri[0]), str(tri[1]), str(tri[2])
        lines.append(f"{h}{sep}{r}{sep}{t}")
    return "\n".join(lines)


def get_evidence(obj: Dict[str, Any]) -> Tuple[List[List[str]], str]:
    """
    Returns (triples, source_field).
    """
    if "evidence_triples" in obj and obj["evidence_triples"] is not None:
        return obj["evidence_triples"], "evidence_triples"
    if "gold_path" in obj and obj["gold_path"] is not None:
        return obj["gold_path"], "gold_path"
    return [], "none"


def build_system_message() -> str:
    return (
        "You are a question-answering system. "
        "Follow the user's instructions exactly. "
        "Only use the provided Knowledge Base facts to answer the question. "
        "Do not output any text outside the requested JSON format."
    )


def build_user_message(
    question_text: str,
    triples_text: str,
    prompting_strategy: str,
    allow_unknown: bool,
) -> str:
    kb_block = triples_text if triples_text.strip() else "(no facts provided)"

    rules = [
        "Use ONLY the facts listed in the Knowledge Base.",
        "Do not use outside knowledge.",
    ]
    if allow_unknown:
        rules.append("If the answer cannot be derived from the facts, return UNKNOWN.")
    else:
        rules.append("Assume the answer is derivable from the facts. Return the best answer.")

    if prompting_strategy == "direct":
        extra = ""
        output_spec = 'Return ONLY a JSON object of the form: {"final_answer": "<ANSWER_OR_UNKNOWN>"}'
    elif prompting_strategy == "scot":
        extra = "Think step by step."
        output_spec = (
            'Return ONLY a JSON object with keys "reasoning" and "final_answer":\n'
            '{"reasoning": ["step 1", "step 2", "..."], "final_answer": "<ANSWER_OR_UNKNOWN>"}\n'
            'Keep each reasoning step short and explicitly grounded in the provided facts. '
            "Do NOT output a separate path representation."
        )
    else:
        raise ValueError(f"Unknown prompting_strategy: {prompting_strategy}")

    rules_text = "\n".join(f"- {r}" for r in rules)

    return (
        "Knowledge Base (triples):\n"
        f"{kb_block}\n\n"
        "Question:\n"
        f"{question_text}\n\n"
        "Rules:\n"
        f"{rules_text}\n\n"
        f"{extra}\n"
        f"{output_spec}"
    ).strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queries_path", required=True, help="Input JSONL queries (optionally with evidence_triples).")
    ap.add_argument("--out_path", required=True, help="Output JSONL prompts.")
    ap.add_argument("--prompting_strategies", nargs="+", default=["direct", "scot"],
                    choices=["direct", "scot"], help="Which prompting strategies to render.")
    ap.add_argument("--triple_sep", default=" | ", help="Separator used to print triples.")
    ap.add_argument("--max_evidence_triples", type=int, default=0,
                    help="If >0, truncate evidence triples to this many (keeps file order).")
    ap.add_argument("--allow_unknown", action="store_true",
                    help="Allow UNKNOWN when facts are insufficient (recommended).")
    ap.add_argument("--system_message", default=None,
                    help="Override default system message text.")
    args = ap.parse_args()

    sys_msg = args.system_message if args.system_message is not None else build_system_message()

    os.makedirs(os.path.dirname(args.out_path) or ".", exist_ok=True)

    num_in = 0
    num_out = 0
    used_evidence = {"evidence_triples": 0, "gold_path": 0, "none": 0}

    with open(args.queries_path, "r", encoding="utf-8") as fin, open(args.out_path, "w", encoding="utf-8") as fout:
        for line in fin:
            if not line.strip():
                continue
            num_in += 1
            obj = json.loads(line)

            qid = str(obj.get("id", f"row{num_in}"))
            question_text = obj.get("question_text") or obj.get("question") or obj.get("question_text_raw")
            if not question_text:
                raise ValueError(f"Missing question_text for id={qid}")

            triples, src = get_evidence(obj)
            used_evidence[src] = used_evidence.get(src, 0) + 1

            if args.max_evidence_triples and args.max_evidence_triples > 0:
                triples = triples[: args.max_evidence_triples]

            triples_text = format_triples(triples, sep=args.triple_sep) if triples else ""

            for strat in args.prompting_strategies:
                user_msg = build_user_message(
                    question_text=str(question_text),
                    triples_text=triples_text,
                    prompting_strategy=strat,
                    allow_unknown=bool(args.allow_unknown),
                )

                out = {
                    "prompt_id": f"{qid}::{strat}",
                    "query_id": qid,
                    "prompting_strategy": strat,
                    "graph_variant": obj.get("graph_variant"),
                    "hop": obj.get("hop"),
                    "template_id": obj.get("template_id"),
                    "intent_key": obj.get("intent_key"),
                    "evidence_source": src,
                    "num_evidence_triples": len(triples),
                    "messages": [
                        {"role": "system", "content": sys_msg},
                        {"role": "user", "content": user_msg},
                    ],
                }
                fout.write(json.dumps(out, ensure_ascii=False) + "\n")
                num_out += 1

    print(json.dumps({
        "queries_path": args.queries_path,
        "out_path": args.out_path,
        "num_in": num_in,
        "num_out": num_out,
        "prompting_strategies": args.prompting_strategies,
        "triple_sep": args.triple_sep,
        "max_evidence_triples": args.max_evidence_triples,
        "allow_unknown": bool(args.allow_unknown),
        "used_evidence": used_evidence,
    }, indent=2))


if __name__ == "__main__":
    main()
