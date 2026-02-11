# Experiment Analysis Report

**Generated:** 2026-02-11 16:59:40

**Total Queries Evaluated:** 50856

---

## Executive Summary

**Best Performing Configuration:**
- Config: `Gemini 3 Pro SC`
- Strategy: `direct`
- EM Score: `1.0000`

### Overall Statistics

- Mean EM: `0.9750`
- Mean F1: `0.9755`
- Path Found Rate: `0.4855`
- Mean Latency: `18830.98` ms
- Total Cost: `$213.2211`
- Avg Cost per Query: `$0.004193`

---

## Configuration Performance Comparison

| Config           |   em_mean |   em_std |   f1_mean |   latency_ms_mean |
|:-----------------|----------:|---------:|----------:|------------------:|
| DeepSeek v3.2 G  |    0.9002 |   0.2998 |    0.9005 |           2656.75 |
| DeepSeek v3.2 SC |    0.9685 |   0.1746 |    0.9688 |          11970.5  |
| GPT-oss G        |    0.9936 |   0.0797 |    0.9945 |          11612.8  |
| GPT-oss SC       |    0.9913 |   0.093  |    0.9915 |          26096.2  |
| Gemini 3 Pro G   |    0.9989 |   0.033  |    0.9997 |           7547.37 |
| Gemini 3 Pro SC  |    1      |   0      |    1      |          90291.7  |
| Llama 4 G        |    0.9715 |   0.1664 |    0.9725 |           1254.33 |
| Llama 4 SC       |    0.9777 |   0.1476 |    0.9783 |           5004.49 |

---

## Performance by Strategy

|                              |   em_mean |   em_std |   f1_mean |   latency_ms_mean |
|:-----------------------------|----------:|---------:|----------:|------------------:|
| ('direct', 'abstract')       |    0.9899 |   0.0998 |    0.99   |           17564.1 |
| ('direct', 'counterfactual') |    0.9313 |   0.253  |    0.9316 |           16616   |
| ('direct', 'natural')        |    0.945  |   0.2279 |    0.9457 |           17141.4 |
| ('scot', 'abstract')         |    0.9957 |   0.0654 |    0.9962 |           21586   |
| ('scot', 'counterfactual')   |    0.9954 |   0.0677 |    0.9962 |           19557.9 |
| ('scot', 'natural')          |    0.9952 |   0.069  |    0.996  |           20698.6 |

---

## Performance by Hop Count

|   hop |   abstract |   counterfactual |   natural |
|------:|-----------:|-----------------:|----------:|
|     1 |     0.9972 |           0.9967 |    0.9958 |
|     2 |     0.991  |           0.9448 |    0.9485 |
|     3 |     0.9884 |           0.9459 |    0.9618 |

---

## Path Redundancy Analysis

|    | variant        |   hop |   count |   stopped_count |   total |   percentage |   stopped_percentage |
|---:|:---------------|------:|--------:|----------------:|--------:|-------------:|---------------------:|
|  0 | abstract       |     1 |     138 |               0 |     400 |      34.5    |                    0 |
|  1 | abstract       |     2 |     202 |               0 |     382 |      52.8796 |                    0 |
|  2 | abstract       |     3 |      96 |               0 |     237 |      40.5063 |                    0 |
|  3 | counterfactual |     1 |     107 |               0 |     400 |      26.75   |                    0 |
|  4 | counterfactual |     2 |     137 |               0 |     400 |      34.25   |                    0 |
|  5 | counterfactual |     3 |     156 |               0 |     373 |      41.8231 |                    0 |
|  6 | natural        |     1 |     140 |               0 |     400 |      35      |                    0 |
|  7 | natural        |     2 |     203 |               0 |     382 |      53.1414 |                    0 |
|  8 | natural        |     3 |      96 |               0 |     237 |      40.5063 |                    0 |

---

---

*End of Report*
