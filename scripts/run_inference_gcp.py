#!/usr/bin/env python3
"""
run_inference_gcp.py

Run LLM inference on prompts using Google Vertex AI.

Features:
- CLI tool
- greedy and self-consistency decoding
- testing / dry-run mode
- JSONL logging with latency, tokens, and raw outputs

Example:
  python run_inference_gcp.py \
    --prompts_path data/prompts.jsonl \
    --out_path results/answers.jsonl \
    --project_id my-gcp-project \
    --location us-central1 \
    --model gemini-1.5-pro \
    --decoding greedy

Self-consistency:
  python run_inference_gcp.py \
    --decoding self_consistency \
    --sc_samples 5 \
    --temperature 0.7
"""

from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from typing import Any, Dict, List

# Vertex AI
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig


# -------------------------
# Utilities
# -------------------------

def load_jsonl(path: str):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def write_jsonl(path: str, records):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def messages_to_prompt(messages: List[Dict[str, str]]) -> str:
    """
    Convert chat-style messages into a single prompt string.
    Gemini models handle this format well.
    """
    parts = []
    for m in messages:
        role = m["role"].upper()
        parts.append(f"{role}:\n{m['content']}")
    return "\n\n".join(parts)


# -------------------------
# Inference
# -------------------------

def run_single_generation(
    model: GenerativeModel,
    prompt: str,
    gen_config: GenerationConfig,
) -> Dict[str, Any]:
    t0 = time.time()
    response = model.generate_content(
        prompt,
        generation_config=gen_config,
    )
    latency = time.time() - t0

    text = response.text if hasattr(response, "text") else ""
    usage = getattr(response, "usage_metadata", None)

    return {
        "text": text,
        "latency_sec": latency,
        "usage": {
            "prompt_tokens": getattr(usage, "prompt_token_count", None),
            "output_tokens": getattr(usage, "candidates_token_count", None),
            "total_tokens": getattr(usage, "total_token_count", None),
        } if usage else None,
    }


# -------------------------
# Main
# -------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompts_path", required=True)
    ap.add_argument("--out_path", required=True)

    # GCP
    ap.add_argument("--project_id", required=True)
    ap.add_argument("--location", default="us-central1")
    ap.add_argument("--model", required=True)

    # Decoding
    ap.add_argument("--decoding", choices=["greedy", "self_consistency"], default="greedy")
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--max_output_tokens", type=int, default=512)
    ap.add_argument("--top_p", type=float, default=1.0)
    ap.add_argument("--sc_samples", type=int, default=5)

    # Testing / control
    ap.add_argument("--limit", type=int, default=0, help="Max prompts to run (0 = no limit)")
    ap.add_argument("--dry_run", action="store_true", help="Do not call model, emit fake outputs")
    ap.add_argument("--flush_every", type=int, default=10)

    args = ap.parse_args()

    # Init Vertex
    if not args.dry_run:
        vertexai.init(project=args.project_id, location=args.location)
        model = GenerativeModel(args.model)
    else:
        model = None

    # Generation config
    if args.decoding == "greedy":
        gen_config = GenerationConfig(
            temperature=0.0,
            top_p=1.0,
            max_output_tokens=args.max_output_tokens,
        )
    else:
        gen_config = GenerationConfig(
            temperature=args.temperature,
            top_p=args.top_p,
            max_output_tokens=args.max_output_tokens,
        )

    buffer = []
    seen = 0

    for obj in load_jsonl(args.prompts_path):
        seen += 1
        if args.limit and seen > args.limit:
            break

        prompt_text = messages_to_prompt(obj["messages"])

        record = {
            "run_id": str(uuid.uuid4()),
            "prompt_id": obj["prompt_id"],
            "query_id": obj["query_id"],
            "model": args.model,
            "decoding": args.decoding,
            "prompting_strategy": obj.get("prompting_strategy"),
            "graph_variant": obj.get("graph_variant"),
            "hop": obj.get("hop"),
            "template_id": obj.get("template_id"),
            "intent_key": obj.get("intent_key"),
            "timestamp": time.time(),
            "responses": [],
        }

        if args.dry_run:
            record["responses"].append({
                "text": '{"final_answer": "TEST"}',
                "latency_sec": 0.0,
                "usage": None,
            })
        else:
            if args.decoding == "greedy":
                out = run_single_generation(model, prompt_text, gen_config)
                record["responses"].append(out)
            else:
                for _ in range(args.sc_samples):
                    out = run_single_generation(model, prompt_text, gen_config)
                    record["responses"].append(out)

        buffer.append(record)

        if len(buffer) >= args.flush_every:
            write_jsonl(args.out_path, buffer)
            buffer.clear()

    if buffer:
        write_jsonl(args.out_path, buffer)

    print(json.dumps({
        "prompts_path": args.prompts_path,
        "out_path": args.out_path,
        "model": args.model,
        "decoding": args.decoding,
        "dry_run": args.dry_run,
        "processed": seen if not args.limit else min(seen, args.limit),
    }, indent=2))


if __name__ == "__main__":
    main()