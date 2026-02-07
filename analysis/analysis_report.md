# Experiment Analysis Report

## Best Performing Model
| model                       |       em |
|:----------------------------|---------:|
| google/gemini-3-pro-preview | 0.618932 |

## Detailed Outcome Breakdown
|                                                                    |   correct |   missed_answer |   parse_error |   wrong_answer |   Total |
|:-------------------------------------------------------------------|----------:|----------------:|--------------:|---------------:|--------:|
| ('deepseek-ai/deepseek-v3.2-maas', 'abstract')                     |     48.95 |           51.05 |          0    |           0    |     100 |
| ('deepseek-ai/deepseek-v3.2-maas', 'counterfactual')               |     45.99 |           53.92 |          0    |           0.09 |     100 |
| ('deepseek-ai/deepseek-v3.2-maas', 'natural')                      |     45.8  |           54    |          0    |           0.2  |     100 |
| ('google/gemini-3-pro-preview', 'abstract')                        |     62.15 |           37.6  |          0.25 |           0    |     100 |
| ('google/gemini-3-pro-preview', 'counterfactual')                  |     64.33 |           35.53 |          0.03 |           0.11 |     100 |
| ('google/gemini-3-pro-preview', 'natural')                         |     59.05 |           40.57 |          0.15 |           0.23 |     100 |
| ('meta/llama-4-maverick-17b-128e-instruct-maas', 'abstract')       |     45.56 |           54.15 |          0.05 |           0.25 |     100 |
| ('meta/llama-4-maverick-17b-128e-instruct-maas', 'counterfactual') |     44.59 |           55.24 |          0.02 |           0.15 |     100 |
| ('meta/llama-4-maverick-17b-128e-instruct-maas', 'natural')        |     44.58 |           55.15 |          0    |           0.27 |     100 |
| ('openai/gpt-oss-120b-maas', 'abstract')                           |     49.93 |           50    |          0    |           0.07 |     100 |
| ('openai/gpt-oss-120b-maas', 'counterfactual')                     |     49.38 |           49.98 |          0    |           0.64 |     100 |
| ('openai/gpt-oss-120b-maas', 'natural')                            |     49.53 |           49.8  |          0    |           0.66 |     100 |

## Metric Summary
| model                                        | decoding         | graph_variant   | prompting_strategy   |       em |       f1 |   latency_ms |   path_found |        cost |
|:---------------------------------------------|:-----------------|:----------------|:---------------------|---------:|---------:|-------------:|-------------:|------------:|
| deepseek-ai/deepseek-v3.2-maas               | greedy           | abstract        | direct               | 0.958783 | 0.958783 |     1922.34  |     0        | 0.000276155 |
| deepseek-ai/deepseek-v3.2-maas               | greedy           | abstract        | scot                 | 0.999019 | 0.999019 |     4586.11  |     0.999019 | 0.000477121 |
| deepseek-ai/deepseek-v3.2-maas               | greedy           | counterfactual  | direct               | 0.842285 | 0.842285 |     1947.63  |     0        | 0.000253276 |
| deepseek-ai/deepseek-v3.2-maas               | greedy           | counterfactual  | scot                 | 0.997442 | 0.997442 |     4448.61  |     1        | 0.000461115 |
| deepseek-ai/deepseek-v3.2-maas               | greedy           | natural         | direct               | 0.835132 | 0.835132 |     1735.23  |     0        | 0.000250306 |
| deepseek-ai/deepseek-v3.2-maas               | greedy           | natural         | scot                 | 0.997056 | 0.997056 |     4309.86  |     0.999019 | 0.000445045 |
| deepseek-ai/deepseek-v3.2-maas               | self_consistency | abstract        | direct               | 0        | 0        |     7429.24  |     0        | 0.00136097  |
| deepseek-ai/deepseek-v3.2-maas               | self_consistency | abstract        | scot                 | 0        | 0        |    19229.2   |     0        | 0.002395    |
| deepseek-ai/deepseek-v3.2-maas               | self_consistency | counterfactual  | direct               | 0        | 0        |     7246.23  |     0        | 0.00125802  |
| deepseek-ai/deepseek-v3.2-maas               | self_consistency | counterfactual  | scot                 | 0        | 0        |    17494.2   |     0        | 0.00227683  |
| deepseek-ai/deepseek-v3.2-maas               | self_consistency | natural         | direct               | 0        | 0        |     7571.21  |     0        | 0.00125071  |
| deepseek-ai/deepseek-v3.2-maas               | self_consistency | natural         | scot                 | 0        | 0        |    17785.4   |     0        | 0.0022112   |
| google/gemini-3-pro-preview                  | greedy           | abstract        | direct               | 0.986261 | 0.986261 |     7155.23  |     0        | 0.00150668  |
| google/gemini-3-pro-preview                  | greedy           | abstract        | scot                 | 0.986261 | 0.986351 |     8045.67  |     0.986261 | 0.00330739  |
| google/gemini-3-pro-preview                  | greedy           | counterfactual  | direct               | 0.992327 | 0.992327 |     6030.77  |     0        | 0.000989511 |
| google/gemini-3-pro-preview                  | greedy           | counterfactual  | scot                 | 0.999147 | 0.999147 |     5888.7   |     0.998295 | 0.00232532  |
| google/gemini-3-pro-preview                  | greedy           | natural         | direct               | 0.986261 | 0.986261 |     6443.26  |     0        | 0.000975847 |
| google/gemini-3-pro-preview                  | greedy           | natural         | scot                 | 0.992149 | 0.992245 |     6185.92  |     0.991168 | 0.00222501  |
| google/gemini-3-pro-preview                  | self_consistency | abstract        | direct               | 0        | 0        |    35350.7   |     0        | 0.00747009  |
| google/gemini-3-pro-preview                  | self_consistency | abstract        | scot                 | 0        | 0        |    40595.9   |     0        | 0.0138653   |
| google/gemini-3-pro-preview                  | self_consistency | counterfactual  | direct               | 0        | 0        |    33432.7   |     0        | 0.004907    |
| google/gemini-3-pro-preview                  | self_consistency | counterfactual  | scot                 | 0        | 0        |    37067.1   |     0        | 0.0101093   |
| google/gemini-3-pro-preview                  | self_consistency | natural         | direct               | 0        | 0        |    32582     |     0        | 0.00483836  |
| google/gemini-3-pro-preview                  | self_consistency | natural         | scot                 | 0        | 0        |    36667.1   |     0        | 0.0099138   |
| meta/llama-4-maverick-17b-128e-instruct-maas | greedy           | abstract        | direct               | 0.90579  | 0.906009 |      900.551 |     0        | 0.000155953 |
| meta/llama-4-maverick-17b-128e-instruct-maas | greedy           | abstract        | scot                 | 0.916585 | 0.916585 |     1129.45  |     0.914622 | 0.000246324 |
| meta/llama-4-maverick-17b-128e-instruct-maas | greedy           | counterfactual  | direct               | 0.860188 | 0.860211 |      881.181 |     0        | 0.000140701 |
| meta/llama-4-maverick-17b-128e-instruct-maas | greedy           | counterfactual  | scot                 | 0.923274 | 0.9237   |     1084.88  |     0.907928 | 0.000229388 |
| meta/llama-4-maverick-17b-128e-instruct-maas | greedy           | natural         | direct               | 0.863592 | 0.864082 |      847.54  |     0        | 0.000138609 |
| meta/llama-4-maverick-17b-128e-instruct-maas | greedy           | natural         | scot                 | 0.919529 | 0.919664 |     1019.8   |     0.886163 | 0.000209216 |
| meta/llama-4-maverick-17b-128e-instruct-maas | self_consistency | abstract        | direct               | 0        | 0        |     3114.92  |     0        | 0.000772823 |
| meta/llama-4-maverick-17b-128e-instruct-maas | self_consistency | abstract        | scot                 | 0        | 0        |     4699.58  |     0        | 0.00125224  |
| meta/llama-4-maverick-17b-128e-instruct-maas | self_consistency | counterfactual  | direct               | 0        | 0        |     3058.73  |     0        | 0.000711017 |
| meta/llama-4-maverick-17b-128e-instruct-maas | self_consistency | counterfactual  | scot                 | 0        | 0        |     4469.17  |     0        | 0.00114577  |
| meta/llama-4-maverick-17b-128e-instruct-maas | self_consistency | natural         | direct               | 0        | 0        |     3084.03  |     0        | 0.000696272 |
| meta/llama-4-maverick-17b-128e-instruct-maas | self_consistency | natural         | scot                 | 0        | 0        |     4424.52  |     0        | 0.00106083  |
| openai/gpt-oss-120b-maas                     | greedy           | abstract        | direct               | 1        | 1        |     1360.36  |     0        | 9.72004e-05 |
| openai/gpt-oss-120b-maas                     | greedy           | abstract        | scot                 | 0.997056 | 0.997056 |     1902.94  |     0.997056 | 0.000132521 |
| openai/gpt-oss-120b-maas                     | greedy           | counterfactual  | direct               | 0.997442 | 0.997869 |     1502.83  |     0        | 9.46943e-05 |
| openai/gpt-oss-120b-maas                     | greedy           | counterfactual  | scot                 | 0.977835 | 0.977835 |     1692.21  |     0.97954  | 0.000125166 |
| openai/gpt-oss-120b-maas                     | greedy           | natural         | direct               | 1        | 1        |     1414     |     0        | 8.63311e-05 |
| openai/gpt-oss-120b-maas                     | greedy           | natural         | scot                 | 0.981354 | 0.981354 |     1587.13  |     0.981354 | 0.00011761  |
| openai/gpt-oss-120b-maas                     | self_consistency | abstract        | direct               | 0        | 0        |     9808.22  |     0        | 0.000499725 |
| openai/gpt-oss-120b-maas                     | self_consistency | abstract        | scot                 | 0        | 0        |    13631.5   |     0        | 0.0006525   |
| openai/gpt-oss-120b-maas                     | self_consistency | counterfactual  | direct               | 0        | 0        |     8054.94  |     0        | 0.00047414  |
| openai/gpt-oss-120b-maas                     | self_consistency | counterfactual  | scot                 | 0        | 0        |    14220.6   |     0        | 0.000610114 |
| openai/gpt-oss-120b-maas                     | self_consistency | natural         | direct               | 0        | 0        |    11341.8   |     0        | 0.000436037 |
| openai/gpt-oss-120b-maas                     | self_consistency | natural         | scot                 | 0        | 0        |    11051.5   |     0        | 0.000570394 |