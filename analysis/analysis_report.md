# Experiment Analysis Report

**Generated:** 2026-02-08 18:19:32

**Total Queries Evaluated:** 48780

---

## Executive Summary

**Best Performing Configuration:**
- Config: `GPT-oss SC`
- Strategy: `direct`
- EM Score: `1.0000`

### Overall Statistics

- Mean EM: `0.9779`
- Mean F1: `0.9780`
- Path Found Rate: `0.2607`
- Mean Latency: `8081.71` ms
- Total Cost: `$70.5331`
- Avg Cost per Query: `$0.001446`

---

## Configuration Performance Comparison

| Config           |   em_mean |   em_std |   f1_mean |   latency_ms_mean |
|:-----------------|----------:|---------:|----------:|------------------:|
| DeepSeek v3.2 G  |    0.9374 |   0.2423 |    0.9374 |          3160.21  |
| DeepSeek v3.2 SC |    0.9799 |   0.1403 |    0.9801 |         12772.3   |
| GPT-oss G        |    0.9921 |   0.0888 |    0.9921 |          1577.58  |
| GPT-oss SC       |    0.9998 |   0.0125 |    0.9998 |         11341.2   |
| Gemini 3 Pro G   |    0.998  |   0.045  |    0.998  |          6545.47  |
| Gemini 3 Pro SC  |    0.9979 |   0.0457 |    0.9979 |         36060.6   |
| Llama 4 G        |    0.96   |   0.196  |    0.9602 |           769.116 |
| Llama 4 SC       |    0.9665 |   0.1799 |    0.9667 |          3737.27  |

---

## Performance by Strategy

|                              |   em_mean |   em_std |   f1_mean |   latency_ms_mean |
|:-----------------------------|----------:|---------:|----------:|------------------:|
| ('direct', 'abstract')       |    0.9861 |   0.1169 |    0.9862 |           6856.52 |
| ('direct', 'counterfactual') |    0.9525 |   0.2128 |    0.9526 |           6200.93 |
| ('direct', 'natural')        |    0.956  |   0.2051 |    0.9561 |           7045.8  |
| ('scot', 'abstract')         |    0.9912 |   0.0934 |    0.9912 |          10115.3  |
| ('scot', 'counterfactual')   |    0.9918 |   0.0905 |    0.9919 |           9172.28 |
| ('scot', 'natural')          |    0.9919 |   0.0894 |    0.992  |           9215.27 |

---

## Performance by Hop Count

|   hop |   abstract |   counterfactual |   natural |
|------:|-----------:|-----------------:|----------:|
|     1 |     0.9875 |           0.989  |    0.9928 |
|     2 |     0.9889 |           0.9639 |    0.9633 |
|     3 |     0.9907 |           0.9609 |    0.9569 |

---

---

*End of Report*
