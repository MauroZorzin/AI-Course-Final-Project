# Experiment Analysis Report

## Best Performing Model
| model                       |       em |
|:----------------------------|---------:|
| google/gemini-3-pro-preview | 0.999215 |

## Detailed Outcome Breakdown
|                                                                    |   correct |   missed_answer |   wrong_answer |   Total |
|:-------------------------------------------------------------------|----------:|----------------:|---------------:|--------:|
| ('deepseek-ai/deepseek-v3.2-maas', 'abstract')                     |     98.18 |            1.77 |           0.05 |     100 |
| ('deepseek-ai/deepseek-v3.2-maas', 'counterfactual')               |     94.67 |            5.26 |           0.06 |     100 |
| ('deepseek-ai/deepseek-v3.2-maas', 'natural')                      |     94.92 |            5.08 |           0    |     100 |
| ('google/gemini-3-pro-preview', 'abstract')                        |     99.75 |            0.25 |           0    |     100 |
| ('google/gemini-3-pro-preview', 'counterfactual')                  |    100    |            0    |           0    |     100 |
| ('google/gemini-3-pro-preview', 'natural')                         |    100    |            0    |           0    |     100 |
| ('meta/llama-4-maverick-17b-128e-instruct-maas', 'abstract')       |     99.52 |            0    |           0.48 |     100 |
| ('meta/llama-4-maverick-17b-128e-instruct-maas', 'counterfactual') |     96.72 |            3.18 |           0.09 |     100 |
| ('meta/llama-4-maverick-17b-128e-instruct-maas', 'natural')        |     97.09 |            2.78 |           0.13 |     100 |
| ('openai/gpt-oss-120b-maas', 'abstract')                           |     99.93 |            0    |           0.07 |     100 |
| ('openai/gpt-oss-120b-maas', 'counterfactual')                     |     99.36 |            0.09 |           0.55 |     100 |
| ('openai/gpt-oss-120b-maas', 'natural')                            |     99.53 |            0    |           0.47 |     100 |

## Metric Summary
| model                                        | decoding         | graph_variant   | prompting_strategy   |       em |       f1 |   latency_ms |   path_found |        cost |
|:---------------------------------------------|:-----------------|:----------------|:---------------------|---------:|---------:|-------------:|-------------:|------------:|
| deepseek-ai/deepseek-v3.2-maas               | greedy           | abstract        | direct               | 0.958783 | 0.958783 |     1922.34  |     0        | 0.000276155 |
| deepseek-ai/deepseek-v3.2-maas               | greedy           | abstract        | scot                 | 0.999019 | 0.999019 |     4586.11  |     0.999019 | 0.000477121 |
| deepseek-ai/deepseek-v3.2-maas               | greedy           | counterfactual  | direct               | 0.842285 | 0.842285 |     1947.63  |     0        | 0.000253276 |
| deepseek-ai/deepseek-v3.2-maas               | greedy           | counterfactual  | scot                 | 0.997442 | 0.997442 |     4448.61  |     0.990622 | 0.000461115 |
| deepseek-ai/deepseek-v3.2-maas               | greedy           | natural         | direct               | 0.835132 | 0.835132 |     1735.23  |     0        | 0.000250306 |
| deepseek-ai/deepseek-v3.2-maas               | greedy           | natural         | scot                 | 0.997056 | 0.997056 |     4309.86  |     0.977429 | 0.000445045 |
| deepseek-ai/deepseek-v3.2-maas               | self_consistency | abstract        | direct               | 0.982336 | 0.982336 |     7429.24  |     0        | 0.00136097  |
| deepseek-ai/deepseek-v3.2-maas               | self_consistency | abstract        | scot                 | 0.987242 | 0.987242 |    19229.2   |     0        | 0.002395    |
| deepseek-ai/deepseek-v3.2-maas               | self_consistency | counterfactual  | direct               | 0.953112 | 0.953879 |     7246.23  |     0        | 0.00125802  |
| deepseek-ai/deepseek-v3.2-maas               | self_consistency | counterfactual  | scot                 | 0.994032 | 0.994032 |    17494.2   |     0        | 0.00227683  |
| deepseek-ai/deepseek-v3.2-maas               | self_consistency | natural         | direct               | 0.964671 | 0.964671 |     7571.21  |     0        | 0.00125071  |
| deepseek-ai/deepseek-v3.2-maas               | self_consistency | natural         | scot                 | 1        | 1        |    17785.4   |     0        | 0.0022112   |
| google/gemini-3-pro-preview                  | greedy           | abstract        | direct               | 1        | 1        |     7012.02  |     0        | 0.00152767  |
| google/gemini-3-pro-preview                  | greedy           | abstract        | scot                 | 1        | 1        |     8003.38  |     1        | 0.00333257  |
| google/gemini-3-pro-preview                  | greedy           | counterfactual  | direct               | 1        | 1        |     5969.96  |     0        | 0.000996424 |
| google/gemini-3-pro-preview                  | greedy           | counterfactual  | scot                 | 1        | 1        |     5886.69  |     0.989761 | 0.0023273   |
| google/gemini-3-pro-preview                  | greedy           | natural         | direct               | 1        | 1        |     6331.73  |     0        | 0.000989441 |
| google/gemini-3-pro-preview                  | greedy           | natural         | scot                 | 1        | 1        |     6096.59  |     0.97725  | 0.00223628  |
| google/gemini-3-pro-preview                  | self_consistency | abstract        | direct               | 1        | 1        |    35725.9   |     0        | 0.00759709  |
| google/gemini-3-pro-preview                  | self_consistency | abstract        | scot                 | 0.986418 | 0.986418 |    41016.4   |     0        | 0.0140676   |
| google/gemini-3-pro-preview                  | self_consistency | counterfactual  | direct               | 1        | 1        |    33617.7   |     0        | 0.00494805  |
| google/gemini-3-pro-preview                  | self_consistency | counterfactual  | scot                 | 1        | 1        |    36978.3   |     0        | 0.0102718   |
| google/gemini-3-pro-preview                  | self_consistency | natural         | direct               | 1        | 1        |    32847.6   |     0        | 0.00491108  |
| google/gemini-3-pro-preview                  | self_consistency | natural         | scot                 | 1        | 1        |    36733     |     0        | 0.01007     |
| meta/llama-4-maverick-17b-128e-instruct-maas | greedy           | abstract        | direct               | 0.989282 | 0.98949  |      667.845 |     0        | 0.000167471 |
| meta/llama-4-maverick-17b-128e-instruct-maas | greedy           | abstract        | scot                 | 1        | 1        |      919.632 |     0.997859 | 0.000268741 |
| meta/llama-4-maverick-17b-128e-instruct-maas | greedy           | counterfactual  | direct               | 0.932532 | 0.932557 |      666.113 |     0        | 0.000152534 |
| meta/llama-4-maverick-17b-128e-instruct-maas | greedy           | counterfactual  | scot                 | 0.998157 | 0.998618 |      890.562 |     0.973272 | 0.000246762 |
| meta/llama-4-maverick-17b-128e-instruct-maas | greedy           | natural         | direct               | 0.937167 | 0.9377   |      625.43  |     0        | 0.000150418 |
| meta/llama-4-maverick-17b-128e-instruct-maas | greedy           | natural         | scot                 | 0.99787  | 0.998017 |      817.678 |     0.941427 | 0.000227041 |
| meta/llama-4-maverick-17b-128e-instruct-maas | self_consistency | abstract        | direct               | 0.991444 | 0.991444 |     3070.61  |     0        | 0.000838339 |
| meta/llama-4-maverick-17b-128e-instruct-maas | self_consistency | abstract        | scot                 | 1        | 1        |     4792.04  |     0        | 0.00136963  |
| meta/llama-4-maverick-17b-128e-instruct-maas | self_consistency | counterfactual  | direct               | 0.941068 | 0.941068 |     3002.95  |     0        | 0.000763263 |
| meta/llama-4-maverick-17b-128e-instruct-maas | self_consistency | counterfactual  | scot                 | 0.997227 | 0.997689 |     4530.57  |     0        | 0.00123541  |
| meta/llama-4-maverick-17b-128e-instruct-maas | self_consistency | natural         | direct               | 0.948498 | 0.949034 |     3022.03  |     0        | 0.000756118 |
| meta/llama-4-maverick-17b-128e-instruct-maas | self_consistency | natural         | scot                 | 1        | 1        |     4477.22  |     0        | 0.00114726  |
| openai/gpt-oss-120b-maas                     | greedy           | abstract        | direct               | 1        | 1        |     1360.36  |     0        | 9.72004e-05 |
| openai/gpt-oss-120b-maas                     | greedy           | abstract        | scot                 | 0.997056 | 0.997056 |     1902.94  |     0.997056 | 0.000132521 |
| openai/gpt-oss-120b-maas                     | greedy           | counterfactual  | direct               | 0.997442 | 0.997869 |     1502.83  |     0        | 9.46943e-05 |
| openai/gpt-oss-120b-maas                     | greedy           | counterfactual  | scot                 | 0.977835 | 0.977835 |     1692.21  |     0.970162 | 0.000125166 |
| openai/gpt-oss-120b-maas                     | greedy           | natural         | direct               | 1        | 1        |     1414     |     0        | 8.63311e-05 |
| openai/gpt-oss-120b-maas                     | greedy           | natural         | scot                 | 0.981354 | 0.981354 |     1587.13  |     0.959764 | 0.00011761  |
| openai/gpt-oss-120b-maas                     | self_consistency | abstract        | direct               | 1        | 1        |     9808.22  |     0        | 0.000499725 |
| openai/gpt-oss-120b-maas                     | self_consistency | abstract        | scot                 | 1        | 1        |    13631.5   |     0        | 0.0006525   |
| openai/gpt-oss-120b-maas                     | self_consistency | counterfactual  | direct               | 1        | 1        |     8054.94  |     0        | 0.00047414  |
| openai/gpt-oss-120b-maas                     | self_consistency | counterfactual  | scot                 | 0.999147 | 0.999147 |    14220.6   |     0        | 0.000610114 |
| openai/gpt-oss-120b-maas                     | self_consistency | natural         | direct               | 1        | 1        |    11341.8   |     0        | 0.000436037 |
| openai/gpt-oss-120b-maas                     | self_consistency | natural         | scot                 | 1        | 1        |    11051.5   |     0        | 0.000570394 |