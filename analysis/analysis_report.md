# Experiment Analysis Report

**Generated:** 2026-02-08 14:18:25

**Total Queries Evaluated:** 47685

---

## Executive Summary

**Best Performing Configuration:**
- Config: `GPT-oss SC`
- Strategy: `direct`
- EM Score: `1.0000`

### Overall Statistics

- Mean EM: `0.9820`
- Mean F1: `0.9820`
- Path Found Rate: `0.2586`
- Mean Latency: `8214.73` ms
- Total Cost: `$69.9374`
- Avg Cost per Query: `$0.001467`

---

## Configuration Performance Comparison

| Config           |   em_mean |   em_std |   f1_mean |   latency_ms_mean |
|:-----------------|----------:|---------:|----------:|------------------:|
| DeepSeek v3.2 G  |    0.9374 |   0.2423 |    0.9374 |          3160.21  |
| DeepSeek v3.2 SC |    0.9799 |   0.1403 |    0.9801 |         12772.3   |
| GPT-oss G        |    0.9921 |   0.0888 |    0.9921 |          1577.58  |
| GPT-oss SC       |    0.9998 |   0.0125 |    0.9998 |         11341.2   |
| Gemini 3 Pro G   |    1      |   0      |    1      |          6517.72  |
| Gemini 3 Pro SC  |    0.9979 |   0.0457 |    0.9979 |         36060.6   |
| Llama 4 G        |    0.9753 |   0.1552 |    0.9755 |           765.241 |
| Llama 4 SC       |    0.9791 |   0.1429 |    0.9793 |          3811.87  |

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

---

*End of Report*
