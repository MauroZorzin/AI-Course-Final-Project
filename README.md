# SPARK: Synthetic Probes for Assessing Reasoning on Knowledge-graphs (Multi-Hop QA)

## Focus

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

## Constraints:

* Same parameters for all models;  
* Same inputs and data for all models;  
* Lowest context and query size;  
* Standardized query templates across prompting strategies;  
* Same system-prompts (if any).

## Metrics

* EM / F1;  
* Accuracy by hop;  
* Override rate;  
* Path precision / recall;  
* Path EM;  
* Tokens / latency / costs.
