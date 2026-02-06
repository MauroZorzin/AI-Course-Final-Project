# Experiment Analysis Report

## Best Performing Model
| model                          |       em |
|:-------------------------------|---------:|
| deepseek-ai/deepseek-v3.2-maas | 0.666667 |

## Detailed Outcome Breakdown
|                                                      |   correct |   missed_answer |   parse_error |   Total |
|:-----------------------------------------------------|----------:|----------------:|--------------:|--------:|
| ('deepseek-ai/deepseek-v3.2-maas', 'abstract')       |     66.67 |            0    |         33.33 |     100 |
| ('deepseek-ai/deepseek-v3.2-maas', 'counterfactual') |     66.67 |           16.67 |         16.67 |     100 |
| ('deepseek-ai/deepseek-v3.2-maas', 'natural')        |     66.67 |           16.67 |         16.67 |     100 |
| ('gemini-2.5-flash', 'abstract')                     |      0    |            0    |        100    |     100 |
| ('gemini-2.5-flash', 'counterfactual')               |     16.67 |            0    |         83.33 |     100 |
| ('gemini-2.5-flash', 'natural')                      |     16.67 |            0    |         83.33 |     100 |

## Metric Summary
| model                          | graph_variant   | prompting_strategy   |       em |       f1 |   latency_ms |
|:-------------------------------|:----------------|:---------------------|---------:|---------:|-------------:|
| deepseek-ai/deepseek-v3.2-maas | abstract        | direct               | 1        | 1        |      794.667 |
| deepseek-ai/deepseek-v3.2-maas | abstract        | scot                 | 0.333333 | 0.349206 |     1613.67  |
| deepseek-ai/deepseek-v3.2-maas | counterfactual  | direct               | 0.666667 | 0.666667 |      766.333 |
| deepseek-ai/deepseek-v3.2-maas | counterfactual  | scot                 | 0.666667 | 0.69281  |     1548     |
| deepseek-ai/deepseek-v3.2-maas | natural         | direct               | 0.666667 | 0.666667 |      885.667 |
| deepseek-ai/deepseek-v3.2-maas | natural         | scot                 | 0.666667 | 0.687179 |     1323.33  |
| gemini-2.5-flash               | abstract        | direct               | 0        | 0        |     2089     |
| gemini-2.5-flash               | abstract        | scot                 | 0        | 0        |     1828.67  |
| gemini-2.5-flash               | counterfactual  | direct               | 0.333333 | 0.333333 |     2252.67  |
| gemini-2.5-flash               | counterfactual  | scot                 | 0        | 0        |     2035     |
| gemini-2.5-flash               | natural         | direct               | 0.333333 | 0.333333 |     3013.33  |
| gemini-2.5-flash               | natural         | scot                 | 0        | 0        |     4461.33  |