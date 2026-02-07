# Experiment Analysis Report

## Best Performing Model
| model                |       em |
|:---------------------|---------:|
| gemini-3-pro-preview | 0.841463 |

## Detailed Outcome Breakdown
|                                                                    |   correct |   missed_answer |   parse_error |   wrong_answer |   Total |
|:-------------------------------------------------------------------|----------:|----------------:|--------------:|---------------:|--------:|
| ('deepseek-ai/deepseek-v3.2-maas', 'abstract')                     |     48.95 |           51.05 |          0    |           0    |     100 |
| ('deepseek-ai/deepseek-v3.2-maas', 'counterfactual')               |     45.99 |           53.92 |          0    |           0.09 |     100 |
| ('deepseek-ai/deepseek-v3.2-maas', 'natural')                      |     45.8  |           54    |          0    |           0.2  |     100 |
| ('gemini-3-pro-preview', 'natural')                                |     84.15 |           13.41 |          0    |           2.44 |     100 |
| ('google/gemini-3-pro-preview', 'abstract')                        |     62.69 |           37.06 |          0.25 |           0    |     100 |
| ('google/gemini-3-pro-preview', 'counterfactual')                  |     64.83 |           35.03 |          0.03 |           0.11 |     100 |
| ('google/gemini-3-pro-preview', 'natural')                         |     58.88 |           40.79 |          0.15 |           0.18 |     100 |
| ('meta/llama-4-maverick-17b-128e-instruct-maas', 'abstract')       |     45.56 |           54.15 |          0.05 |           0.25 |     100 |
| ('meta/llama-4-maverick-17b-128e-instruct-maas', 'counterfactual') |     44.59 |           55.24 |          0.02 |           0.15 |     100 |
| ('meta/llama-4-maverick-17b-128e-instruct-maas', 'natural')        |     44.58 |           55.15 |          0    |           0.27 |     100 |
| ('openai/gpt-oss-120b-maas', 'abstract')                           |     49.93 |           50    |          0    |           0.07 |     100 |
| ('openai/gpt-oss-120b-maas', 'counterfactual')                     |     49.38 |           49.98 |          0    |           0.64 |     100 |
| ('openai/gpt-oss-120b-maas', 'natural')                            |     49.53 |           49.8  |          0    |           0.66 |     100 |

## Metric Summary
| model                                        | graph_variant   | prompting_strategy   |       em |       f1 |   latency_ms |        cost |
|:---------------------------------------------|:----------------|:---------------------|---------:|---------:|-------------:|------------:|
| deepseek-ai/deepseek-v3.2-maas               | abstract        | direct               | 0.479392 | 0.479392 |      4675.79 | 0.000818563 |
| deepseek-ai/deepseek-v3.2-maas               | abstract        | scot                 | 0.499509 | 0.499509 |     11907.7  | 0.00143606  |
| deepseek-ai/deepseek-v3.2-maas               | counterfactual  | direct               | 0.421142 | 0.421142 |      4596.93 | 0.00075565  |
| deepseek-ai/deepseek-v3.2-maas               | counterfactual  | scot                 | 0.498721 | 0.498721 |     10971.4  | 0.00136897  |
| deepseek-ai/deepseek-v3.2-maas               | natural         | direct               | 0.417566 | 0.417566 |      4653.22 | 0.000750508 |
| deepseek-ai/deepseek-v3.2-maas               | natural         | scot                 | 0.498528 | 0.498528 |     11047.6  | 0.00132812  |
| gemini-3-pro-preview                         | natural         | direct               | 0.847826 | 0.847826 |      8309.3  | 0           |
| gemini-3-pro-preview                         | natural         | scot                 | 0.833333 | 0.833333 |      9426.75 | 0           |
| google/gemini-3-pro-preview                  | abstract        | direct               | 0.626949 | 0.626949 |     17321.2  | 0.003678    |
| google/gemini-3-pro-preview                  | abstract        | scot                 | 0.626949 | 0.627006 |     19845.4  | 0.00712912  |
| google/gemini-3-pro-preview                  | counterfactual  | direct               | 0.645949 | 0.645949 |     15551.2  | 0.00235546  |
| google/gemini-3-pro-preview                  | counterfactual  | scot                 | 0.65075  | 0.65075  |     16627.8  | 0.00502887  |
| google/gemini-3-pro-preview                  | natural         | direct               | 0.58581  | 0.58581  |     17013.2  | 0.00254279  |
| google/gemini-3-pro-preview                  | natural         | scot                 | 0.591677 | 0.591736 |     18344    | 0.00532609  |
| meta/llama-4-maverick-17b-128e-instruct-maas | abstract        | direct               | 0.452895 | 0.453004 |      2007.74 | 0.000464388 |
| meta/llama-4-maverick-17b-128e-instruct-maas | abstract        | scot                 | 0.458292 | 0.458292 |      2914.52 | 0.000749281 |
| meta/llama-4-maverick-17b-128e-instruct-maas | counterfactual  | direct               | 0.430094 | 0.430105 |      1969.95 | 0.000425859 |
| meta/llama-4-maverick-17b-128e-instruct-maas | counterfactual  | scot                 | 0.461637 | 0.46185  |      2777.03 | 0.00068758  |
| meta/llama-4-maverick-17b-128e-instruct-maas | natural         | direct               | 0.431796 | 0.432041 |      1965.78 | 0.000417441 |
| meta/llama-4-maverick-17b-128e-instruct-maas | natural         | scot                 | 0.459764 | 0.459832 |      2722.16 | 0.000635023 |
| openai/gpt-oss-120b-maas                     | abstract        | direct               | 0.5      | 0.5      |      5584.29 | 0.000298463 |
| openai/gpt-oss-120b-maas                     | abstract        | scot                 | 0.498528 | 0.498528 |      7767.24 | 0.00039251  |
| openai/gpt-oss-120b-maas                     | counterfactual  | direct               | 0.498721 | 0.498934 |      4778.88 | 0.000284417 |
| openai/gpt-oss-120b-maas                     | counterfactual  | scot                 | 0.488917 | 0.488917 |      7956.39 | 0.00036764  |
| openai/gpt-oss-120b-maas                     | natural         | direct               | 0.5      | 0.5      |      6377.9  | 0.000261184 |
| openai/gpt-oss-120b-maas                     | natural         | scot                 | 0.490677 | 0.490677 |      6319.3  | 0.000344002 |