# Experiment Analysis Report

**Generated:** 2026-02-09 11:17:22

**Total Queries Evaluated:** 51376

---

## Executive Summary

**Best Performing Configuration:**
- Config: `GPT-oss SC`
- Strategy: `direct`
- EM Score: `1.0000`

### Overall Statistics

- Mean EM: `0.9827`
- Mean F1: `0.9828`
- Path Found Rate: `0.4768`
- Mean Latency: `10040.56` ms
- Total Cost: `$96.5703`
- Avg Cost per Query: `$0.001880`

---

## Configuration Performance Comparison

| Config           |   em_mean |   em_std |   f1_mean |   latency_ms_mean |
|:-----------------|----------:|---------:|----------:|------------------:|
| DeepSeek v3.2 G  |    0.9374 |   0.2423 |    0.9374 |          3160.21  |
| DeepSeek v3.2 SC |    0.9799 |   0.1403 |    0.9801 |         12772.3   |
| GPT-oss G        |    0.9921 |   0.0888 |    0.9921 |          1577.58  |
| GPT-oss SC       |    0.9998 |   0.0125 |    0.9998 |         11341.2   |
| Gemini 3 Pro G   |    0.998  |   0.045  |    0.998  |          6556.53  |
| Gemini 3 Pro SC  |    0.9988 |   0.0353 |    0.9988 |         40381.9   |
| Llama 4 G        |    0.9752 |   0.1554 |    0.9755 |           760.608 |
| Llama 4 SC       |    0.9807 |   0.1376 |    0.9808 |          3774.12  |

---

## Performance by Strategy

|                              |   em_mean |   em_std |   f1_mean |   latency_ms_mean |
|:-----------------------------|----------:|---------:|----------:|------------------:|
| ('direct', 'abstract')       |    0.9904 |   0.0974 |    0.9905 |           8906.53 |
| ('direct', 'counterfactual') |    0.9584 |   0.1996 |    0.9586 |           8186.41 |
| ('direct', 'natural')        |    0.9612 |   0.193  |    0.9614 |           8631.4  |
| ('scot', 'abstract')         |    0.9961 |   0.0625 |    0.9961 |          12509.3  |
| ('scot', 'counterfactual')   |    0.9954 |   0.0675 |    0.9955 |          11261    |
| ('scot', 'natural')          |    0.9966 |   0.0585 |    0.9966 |          10844.5  |

---

## Performance by Hop Count

|   hop |   abstract |   counterfactual |   natural |
|------:|-----------:|-----------------:|----------:|
|     1 |     0.9942 |           0.9959 |    0.998  |
|     2 |     0.9923 |           0.9683 |    0.9668 |
|     3 |     0.9931 |           0.9658 |    0.9662 |

---

---

*End of Report*
