# ConfigStream Architecture

## Overview
ConfigStream is a Zero-Budget, Serverless Cyber Threat Intelligence (CTI) pipeline for proxy aggregation and verification.

## Core Components

### 1. Intelligence Layer
- **Anomaly Detection**: Uses Isolation Forest ML to detect spam attacks and cache poisoning.
- **Source Quality**: Scores sources based on Reliability, Diversity, and Consistency.
- **Smart Scheduling**: Retests proxies based on their health score (predictive maintenance).

### 2. Networking Layer
- **Fetcher**: Robust async fetcher with AIMD timeouts and Jitter Analysis.
- **Circuit Breakers**: Protects against thundering herd problems.
- **DNS Pre-warming**: Optimizes connection times.

### 3. Security Layer
- **uTLS Sidecar**: Go binary for mimicking browser TLS fingerprints.
- **Honeypot Detection**: Passive VirusTotal checks (No active scanning).
- **Blocklists**: Filters known malicious IPs (FireHol Level 1).

## Pipeline Flow
1. **Fetch**: Download sources (Github, URL).
2. **Filter**: Deduplicate, check blocklists.
3. **Parse**: normalize to standard Proxy model.
4. **Verify**:
   - Check Latency.
   - Check Region/ASN.
   - Check Anomaly/Jitter.
5. **Output**: Generate subscriptions, JSON, and Metadata.

## Deployment
- **GitHub Actions**: Runs the pipeline (Matrix strategy).
- **GitHub Pages**: Hosts the output artifacts.
- **Docker**: For local development.
