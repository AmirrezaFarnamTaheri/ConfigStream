# Zero to Hero: The ConfigStream Manifesto

## The Mission
To build the world's most resilient, censorship-resistant proxy aggregation network **without spending a single dollar**.

## The Constraint: "Zero Budget"
Most proxy aggregators rely on expensive VPS fleets, paid GeoIP databases, and premium proxy pools. We reject this.
**ConfigStream operates entirely on free tier infrastructure.**

*   **Compute:** GitHub Actions (Standard Runners)
*   **Hosting:** GitHub Pages
*   **Database:** SQLite (Artifact-passed) + JSON Static Files
*   **Intelligence:** Public APIs (VirusTotal Free Tier) + Client-Side Compute (WASM)

## The "No Abuse" Pledge
We do not scan ports. We do not bruteforce. We do not scrape aggressively.
*   **Passive Verification Only:** We check if a proxy is listed in reputation databases rather than knocking on its SSH port.
*   **Respectful Fetching:** We use `If-Modified-Since` headers and strict rate limiting.

## Roadmap

### Phase 1: The Core (Completed)
*   Hybrid Python/Go Pipeline
*   Sing-box Integration
*   Basic Deduplication

### Phase 2: The Shield (Current)
*   **Proxy Washing:** Using WARP to clean dirty IPs.
*   **Smart Routing:** Intranet Bridges.
*   **Static Vectors:** Client-side similarity search.

### Phase 3: The Cloud (Next)
*   **WASM Distributed Testing:** Offloading verification to user browsers.
*   **Decentralized Mirrors:** Automatic syncing to GitLab/HuggingFace.
