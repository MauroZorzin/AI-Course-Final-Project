# SPARK: Synthetic Probes for Assessing Reasoning on Knowledge-graphs (Multi-Hop QA)

## Project details

### Focus

* **Hop length**: 1 to 3;  
* **Prompting strategies**:  
  * Direct;  
  * Structured CoT (sCoT).  
* **Decoding strategies** (*funds-depending, model-depending, time-depending*):  
  * Greedy;  
  * [Self-Consistency](https://iclr.cc/virtual/2023/poster/11718).  
* **Graph structure**:  
  * **Natural** (**baseline**): tests retrieval \+ basic reasoning;  
  * **Abstract** (**renaming nodes**): semantic is removed, tests pure symbolic logic;  
  * **Counterfactual** (**real names, fake facts**): tests context adherence.  
* **Models**:  
  * Gemini 3 Pro;  
  * DeepSeek-V3.2;  
  * Llama 4 Maverick;  
  * Claude & OpenAI (*funds-depending*);  
  * A free, open-source model (*time-depending*).  
* **Accuracy vs efficiency trade-off**:  
  * Latency;  
  * Total tokens;  
  * Cost per query.

### Constraints:

* Same parameters for all models;  
* Same inputs and data for all models;  
* Lowest context and query size;  
* Standardized query templates across prompting strategies;  
* Same system-prompts (if any).

### Metrics

* EM / F1;  
* Accuracy by hop;  
* Override rate;  
* Path precision / recall;  
* Path EM;  
* Tokens / latency / costs.

## Commands

```shell
mamba create -n ai-proj python=3.12

mamba activate ai-proj

mamba install google-genai, google-api-core, google-cloud-aiplatform, seaborn, tabulate
```

```shell
python .\build_graph_variants.py --kb_path MetaQA/kb.txt --out_dir sources/graphs
```

```shell
python .\scripts\make_templates.py --graph_path .\sources\graphs\natural.kb --out_path sources/queries/templates/natural

python .\scripts\make_templates.py --graph_path .\sources\graphs\abstract.kb --out_path sources/queries/templates/abstract

python .\scripts\make_templates.py --graph_path .\sources\graphs\counterfactual.kb --out_path sources/queries/templates/counterfactual
```

```shell
python .\scripts\instantiate_queries.py --graph_path .\sources\graphs\natural.kb --graph_variant_name natural --templates_path .\sources\queries\templates\natural.jsonl --out_path sources/queries/instances/natural.jsonl --instances_per_hop 400

python .\scripts\instantiate_queries.py --graph_path .\sources\graphs\abstract.kb --graph_variant_name abstract --templates_path .\sources\queries\templates\abstract.jsonl --out_path sources/queries/instances/abstract.jsonl --instances_per_hop 400

python .\scripts\instantiate_queries.py --graph_path .\sources\graphs\counterfactual.kb --graph_variant_name counterfactual --templates_path .\sources\queries\templates\counterfactual.jsonl --out_path sources/queries/instances/counterfactual.jsonl --instances_per_hop 400
```

```shell
python .\scripts\extract_subgraphs.py --graph_path .\sources\graphs\natural.kb --queries_path .\sources\queries\instances\natural.jsonl --out_path .\sources\queries\natural.jsonl

python .\scripts\extract_subgraphs.py --graph_path .\sources\graphs\abstract.kb --queries_path .\sources\queries\instances\abstract.jsonl --out_path .\sources\queries\abstract.jsonl

python .\scripts\extract_subgraphs.py --graph_path .\sources\graphs\counterfactual.kb --queries_path .\sources\queries\instances\counterfactual.jsonl --out_path .\sources\queries\counterfactual.jsonl
```

```shell
python .\scripts\render_prompts.py --queries_path .\sources\queries\natural.jsonl --out_path sources/prompts/natural.jsonl --allow_unknown

python .\scripts\render_prompts.py --queries_path .\sources\queries\abstract.jsonl --out_path sources/prompts/abstract.jsonl --allow_unknown

python .\scripts\render_prompts.py --queries_path .\sources\queries\counterfactual.jsonl --out_path sources/prompts/counterfactual.jsonl --allow_unknown
```

```shell
python .\scripts\run_sweep_gcp.py --config .\config\natural.json --parallel

python .\scripts\run_sweep_gcp.py --config .\config\abstract.json --parallel

python .\scripts\run_sweep_gcp.py --config .\config\counterfactual.json --parallel
```

```shell
python scripts/clean_responses.py
```

```shell
python scripts/evaluate.py --queries sources/queries/instances --responses out --config config/natural.json --natural_queries sources/queries/instances/natural.jsonl --out_dir eval
```

```shell
python scripts/analysis.py --eval eval --out_dir analysis --make_plots
```
