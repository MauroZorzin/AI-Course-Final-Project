# Experiment Analysis Report

**Generated:** 2026-02-07 21:38:53

**Total Queries Evaluated:** 47685

---

## Executive Summary

**Best Performing Configuration:**
- Model: `google/gemini-3-pro-preview`
- Decoding: `greedy`
- Strategy: `scot`
- EM Score: `1.0000`

### Overall Statistics

- Mean EM: `0.9820`
- Mean F1: `0.9820`
- Path Found Rate: `0.2586`
- Mean Latency: `8214.73` ms
- Total Cost: `$69.9374`
- Avg Cost per Query: `$0.001467`

---

## Detailed Outcome Breakdown

### Outcome Percentages by Model and Graph Variant

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

---

## Performance by Strategy

|                              |   em_mean |   em_std |   f1_mean |   latency_ms_mean |
|:-----------------------------|----------:|---------:|----------:|------------------:|
| ('direct', 'abstract')       |    0.9897 |   0.1012 |    0.9897 |           6971.52 |
| ('direct', 'counterfactual') |    0.9562 |   0.2048 |    0.9563 |           6293.16 |
| ('direct', 'natural')        |    0.9593 |   0.1977 |    0.9594 |           7162.22 |
| ('scot', 'abstract')         |    0.9967 |   0.0575 |    0.9967 |          10305.6  |
| ('scot', 'counterfactual')   |    0.9952 |   0.0694 |    0.9953 |           9316.45 |
| ('scot', 'natural')          |    0.9969 |   0.0559 |    0.9969 |           9361.98 |

---

## Performance by Hop Count

|   hop |   abstract |   counterfactual |   natural |
|------:|-----------:|-----------------:|----------:|
|     1 |     0.994  |           0.9961 |    0.9979 |
|     2 |     0.992  |           0.9673 |    0.9661 |
|     3 |     0.9936 |           0.9612 |    0.9622 |

---

## Comprehensive Metric Summary

|                                                                                                  |   em_mean |   f1_mean |   latency_ms_mean |   total_tokens_mean |   path_found_mean |   cost_mean |   cost_sum |
|:-------------------------------------------------------------------------------------------------|----------:|----------:|------------------:|--------------------:|------------------:|------------:|-----------:|
| ('deepseek-ai/deepseek-v3.2-maas', 'greedy', 'abstract', 'direct')                               |    0.9588 |    0.9588 |          1922.34  |             469.103 |            0      |      0.0003 |     0.2814 |
| ('deepseek-ai/deepseek-v3.2-maas', 'greedy', 'abstract', 'scot')                                 |    0.999  |    0.999  |          4586.11  |             624.059 |            0.999  |      0.0005 |     0.4862 |
| ('deepseek-ai/deepseek-v3.2-maas', 'greedy', 'counterfactual', 'direct')                         |    0.8423 |    0.8423 |          1947.63  |             429.672 |            0      |      0.0003 |     0.2971 |
| ('deepseek-ai/deepseek-v3.2-maas', 'greedy', 'counterfactual', 'scot')                           |    0.9974 |    0.9974 |          4448.61  |             588.719 |            0.9906 |      0.0005 |     0.5409 |
| ('deepseek-ai/deepseek-v3.2-maas', 'greedy', 'natural', 'direct')                                |    0.8351 |    0.8351 |          1735.23  |             424.883 |            0      |      0.0003 |     0.2551 |
| ('deepseek-ai/deepseek-v3.2-maas', 'greedy', 'natural', 'scot')                                  |    0.9971 |    0.9971 |          4309.86  |             576.133 |            0.9774 |      0.0004 |     0.4535 |
| ('deepseek-ai/deepseek-v3.2-maas', 'self_consistency', 'abstract', 'direct')                     |    0.9823 |    0.9823 |          7429.24  |            2312.05  |            0      |      0.0014 |     1.3868 |
| ('deepseek-ai/deepseek-v3.2-maas', 'self_consistency', 'abstract', 'scot')                       |    0.9872 |    0.9872 |         19229.2   |            3101.37  |            0      |      0.0024 |     2.4405 |
| ('deepseek-ai/deepseek-v3.2-maas', 'self_consistency', 'counterfactual', 'direct')               |    0.9531 |    0.9539 |          7246.23  |            2135.06  |            0      |      0.0013 |     1.4757 |
| ('deepseek-ai/deepseek-v3.2-maas', 'self_consistency', 'counterfactual', 'scot')                 |    0.994  |    0.994  |         17494.2   |            2914.2   |            0      |      0.0023 |     2.6707 |
| ('deepseek-ai/deepseek-v3.2-maas', 'self_consistency', 'natural', 'direct')                      |    0.9647 |    0.9647 |          7571.21  |            2123.93  |            0      |      0.0013 |     1.2745 |
| ('deepseek-ai/deepseek-v3.2-maas', 'self_consistency', 'natural', 'scot')                        |    1      |    1      |         17785.4   |            2871.43  |            0      |      0.0022 |     2.2532 |
| ('google/gemini-3-pro-preview', 'greedy', 'abstract', 'direct')                                  |    1      |    1      |          7012.02  |            1023.69  |            0      |      0.0015 |     1.5353 |
| ('google/gemini-3-pro-preview', 'greedy', 'abstract', 'scot')                                    |    1      |    1      |          8003.38  |            1157.1   |            1      |      0.0033 |     3.3492 |
| ('google/gemini-3-pro-preview', 'greedy', 'counterfactual', 'direct')                            |    1      |    1      |          5969.96  |             750.144 |            0      |      0.001  |     1.1598 |
| ('google/gemini-3-pro-preview', 'greedy', 'counterfactual', 'scot')                              |    1      |    1      |          5886.69  |             817.534 |            0.9898 |      0.0023 |     2.7276 |
| ('google/gemini-3-pro-preview', 'greedy', 'natural', 'direct')                                   |    1      |    1      |          6331.73  |             760.096 |            0      |      0.001  |     0.9944 |
| ('google/gemini-3-pro-preview', 'greedy', 'natural', 'scot')                                     |    1      |    1      |          6096.59  |             820.931 |            0.9773 |      0.0022 |     2.2609 |
| ('google/gemini-3-pro-preview', 'self_consistency', 'abstract', 'direct')                        |    1      |    1      |         35725.9   |            4981.15  |            0      |      0.0076 |     4.4899 |
| ('google/gemini-3-pro-preview', 'self_consistency', 'abstract', 'scot')                          |    0.9864 |    0.9864 |         41016.4   |            5780.04  |            0      |      0.0141 |     8.2858 |
| ('google/gemini-3-pro-preview', 'self_consistency', 'counterfactual', 'direct')                  |    1      |    1      |         33617.7   |            3670.4   |            0      |      0.0049 |     3.1816 |
| ('google/gemini-3-pro-preview', 'self_consistency', 'counterfactual', 'scot')                    |    1      |    1      |         36978.3   |            4231.26  |            0      |      0.0103 |     6.5534 |
| ('google/gemini-3-pro-preview', 'self_consistency', 'natural', 'direct')                         |    1      |    1      |         32847.6   |            3640.62  |            0      |      0.0049 |     3.3543 |
| ('google/gemini-3-pro-preview', 'self_consistency', 'natural', 'scot')                           |    1      |    1      |         36733     |            4213.24  |            0      |      0.0101 |     6.8678 |
| ('meta/llama-4-maverick-17b-128e-instruct-maas', 'greedy', 'abstract', 'direct')                 |    0.9893 |    0.9895 |           667.845 |             452.078 |            0      |      0.0002 |     0.1563 |
| ('meta/llama-4-maverick-17b-128e-instruct-maas', 'greedy', 'abstract', 'scot')                   |    1      |    1      |           919.632 |             574.215 |            0.9979 |      0.0003 |     0.251  |
| ('meta/llama-4-maverick-17b-128e-instruct-maas', 'greedy', 'counterfactual', 'direct')           |    0.9325 |    0.9326 |           666.113 |             411.832 |            0      |      0.0002 |     0.165  |
| ('meta/llama-4-maverick-17b-128e-instruct-maas', 'greedy', 'counterfactual', 'scot')             |    0.9982 |    0.9986 |           890.562 |             527.83  |            0.9733 |      0.0002 |     0.2677 |
| ('meta/llama-4-maverick-17b-128e-instruct-maas', 'greedy', 'natural', 'direct')                  |    0.9372 |    0.9377 |           625.43  |             407.273 |            0      |      0.0002 |     0.1412 |
| ('meta/llama-4-maverick-17b-128e-instruct-maas', 'greedy', 'natural', 'scot')                    |    0.9979 |    0.998  |           817.678 |             508.02  |            0.9414 |      0.0002 |     0.2132 |
| ('meta/llama-4-maverick-17b-128e-instruct-maas', 'self_consistency', 'abstract', 'direct')       |    0.9914 |    0.9914 |          3070.61  |            2261.56  |            0      |      0.0008 |     0.7838 |
| ('meta/llama-4-maverick-17b-128e-instruct-maas', 'self_consistency', 'abstract', 'scot')         |    1      |    1      |          4792.04  |            2894     |            0      |      0.0014 |     1.2669 |
| ('meta/llama-4-maverick-17b-128e-instruct-maas', 'self_consistency', 'counterfactual', 'direct') |    0.9411 |    0.9411 |          3002.95  |            2059.38  |            0      |      0.0008 |     0.8289 |
| ('meta/llama-4-maverick-17b-128e-instruct-maas', 'self_consistency', 'counterfactual', 'scot')   |    0.9972 |    0.9977 |          4530.57  |            2640.27  |            0      |      0.0012 |     1.3367 |
| ('meta/llama-4-maverick-17b-128e-instruct-maas', 'self_consistency', 'natural', 'direct')        |    0.9485 |    0.949  |          3022.03  |            2040.24  |            0      |      0.0008 |     0.7047 |
| ('meta/llama-4-maverick-17b-128e-instruct-maas', 'self_consistency', 'natural', 'scot')          |    1      |    1      |          4477.22  |            2550.57  |            0      |      0.0011 |     1.075  |
| ('openai/gpt-oss-120b-maas', 'greedy', 'abstract', 'direct')                                     |    1      |    1      |          1360.36  |             642.181 |            0      |      0.0001 |     0.099  |
| ('openai/gpt-oss-120b-maas', 'greedy', 'abstract', 'scot')                                       |    0.9971 |    0.9971 |          1902.94  |             777.042 |            0.9971 |      0.0001 |     0.135  |
| ('openai/gpt-oss-120b-maas', 'greedy', 'counterfactual', 'direct')                               |    0.9974 |    0.9979 |          1502.83  |             603.391 |            0      |      0.0001 |     0.1111 |
| ('openai/gpt-oss-120b-maas', 'greedy', 'counterfactual', 'scot')                                 |    0.9778 |    0.9778 |          1692.21  |             724.785 |            0.9702 |      0.0001 |     0.1468 |
| ('openai/gpt-oss-120b-maas', 'greedy', 'natural', 'direct')                                      |    1      |    1      |          1414     |             577.334 |            0      |      0.0001 |     0.088  |
| ('openai/gpt-oss-120b-maas', 'greedy', 'natural', 'scot')                                        |    0.9814 |    0.9814 |          1587.13  |             700.97  |            0.9598 |      0.0001 |     0.1198 |
| ('openai/gpt-oss-120b-maas', 'self_consistency', 'abstract', 'direct')                           |    1      |    1      |          9808.22  |            3228.84  |            0      |      0.0005 |     0.5092 |
| ('openai/gpt-oss-120b-maas', 'self_consistency', 'abstract', 'scot')                             |    1      |    1      |         13631.5   |            3837.41  |            0      |      0.0007 |     0.6649 |
| ('openai/gpt-oss-120b-maas', 'self_consistency', 'counterfactual', 'direct')                     |    1      |    1      |          8054.94  |            3001.53  |            0      |      0.0005 |     0.5562 |
| ('openai/gpt-oss-120b-maas', 'self_consistency', 'counterfactual', 'scot')                       |    0.9991 |    0.9991 |         14220.6   |            3556.56  |            0      |      0.0006 |     0.7157 |
| ('openai/gpt-oss-120b-maas', 'self_consistency', 'natural', 'direct')                            |    1      |    1      |         11341.8   |            2886.21  |            0      |      0.0004 |     0.4443 |
| ('openai/gpt-oss-120b-maas', 'self_consistency', 'natural', 'scot')                              |    1      |    1      |         11051.5   |            3441.07  |            0      |      0.0006 |     0.5812 |

---

## Key Insights

### Best Configuration per Graph Variant

**Abstract:** google/gemini-3-pro-preview with direct strategy (EM: 1.0000)

**Counterfactual:** google/gemini-3-pro-preview with scot strategy (EM: 1.0000)

**Natural:** google/gemini-3-pro-preview with scot strategy (EM: 1.0000)

### Strategy Effectiveness

- **SCOT**: 0.9962 average EM
- **DIRECT**: 0.9677 average EM

### Most Common Failure Modes

- **Missed_answer**: 780 occurrences (1.64%)
- **Wrong_answer**: 80 occurrences (0.17%)

---

## Cost Efficiency Analysis

### Cost per EM Point (Lower is Better)

| model                                        | prompting_strategy   |       em |        cost |   cost_per_em_point |
|:---------------------------------------------|:---------------------|---------:|------------:|--------------------:|
| openai/gpt-oss-120b-maas                     | direct               | 0.999533 | 0.000281502 |            0.000282 |
| openai/gpt-oss-120b-maas                     | scot                 | 0.99237  | 0.000368031 |            0.000371 |
| meta/llama-4-maverick-17b-128e-instruct-maas | direct               | 0.955646 | 0.000470626 |            0.000492 |
| meta/llama-4-maverick-17b-128e-instruct-maas | scot                 | 0.998814 | 0.000747296 |            0.000748 |
| deepseek-ai/deepseek-v3.2-maas               | direct               | 0.92152  | 0.000773983 |            0.00084  |
| deepseek-ai/deepseek-v3.2-maas               | scot                 | 0.995796 | 0.0013773   |            0.001383 |
| google/gemini-3-pro-preview                  | direct               | 1        | 0.00289045  |            0.00289  |
| google/gemini-3-pro-preview                  | scot                 | 0.99843  | 0.00589459  |            0.005904 |

---

*End of Report*
