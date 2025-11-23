# ConfigStream Wiki

Welcome to the **ConfigStream** documentation. This wiki serves as the definitive guide for users, developers, and contributors.

## 📚 Core Documentation

### 1. Introduction & Philosophy
[**01-introduction.md**](01-introduction.md)
*   The vision: "Unstoppable Access"
*   The "Zero Budget" architecture
*   Design principles and core values

### 2. Architecture & Design
[**02-architecture.md**](02-architecture.md)
*   High-level system overview
*   The Hybrid Engine (Python + Go)
*   Pipeline stages and data flow
*   Memory management and concurrency models

### 3. Protocols & Parsing
[**03-protocols.md**](03-protocols.md)
*   Supported protocols (Shadowsocks, VMess, VLESS, Trojan, Hysteria 2, Tuic, WireGuard, SSH)
*   Parsing logic and validation strategies
*   Client compatibility (Clash, Sing-box, Surge, Loon, etc.)

### 4. Engineering & Internals
[**04-engineering.md**](04-engineering.md)
*   Detailed component analysis
*   The `SingBoxTester` and Go Sidecar
*   Adaptive timeout and concurrency management
*   Intelligence layers (Source Quality, Anomaly Detection)

### 5. DevOps & Infrastructure
[**05-devops.md**](05-devops.md)
*   CI/CD pipeline architecture (GitHub Actions)
*   Caching strategies and artifact management
*   Docker and local development
*   Security practices (dependabot, secret scanning)

### 6. Frontend & User Experience
[**06-frontend.md**](06-frontend.md)
*   PWA architecture and "Cache-First" strategy
*   Visualization (Globe.gl, Charts.js)
*   WASM client-side testing
*   Internationalization (i18n)

### 7. Security & Privacy
[**07-security.md**](07-security.md)
*   The "No Abuse" pledge
*   Honeypot detection and blocklists
*   Proxy Washing and sanitization
*   TLS fingerprinting (uTLS)

### 8. API Reference
[**08-api-reference.md**](08-api-reference.md)
*   CLI commands and arguments
*   REST API endpoints (FastAPI)
*   Metadata formats and JSON schemas

### 9. Contributor Guide
[**09-contributing.md**](09-contributing.md)
*   Setting up the development environment
*   Coding standards and style guides
*   Testing requirements and workflows
*   How to submit a Pull Request

## 🧭 Navigation
Use the sidebar or the links above to navigate through the documentation.
