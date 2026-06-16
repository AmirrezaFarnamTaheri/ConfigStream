# ConfigStream v2.0 Architecture

 ConfigStream v2.0 introduces advanced features for censorship resilience, decentralized infrastructure, and improved security.

 ## 1. Steganographic Delivery ("The Gallery")
 - **Objective:** Bypass DPI by disguising configs as images.
 - **Implementation:** Polyglot PNG+Zip files.
 - **Usage:** Clients download `gallery.png`, which renders as a normal image but contains an encrypted Zip payload.

 ## 2. IPFS Dead Man's Switch
 - **Objective:** Censorship-resistant fallback.
 - **Implementation:** Daily snapshots pinned to IPFS/IPNS.
 - **Failover:** If `github.io` is blocked, the client switches to IPFS gateways.
 - **Requirement:** The `publish_ipfs.py` script requires a local `ipfs` node daemon running to publish IPNS updates, or a pinning service with API support.

 ## 3. "Bring Your Own Worker" (BYOW)
 - **Objective:** Decentralize the exit node infrastructure.
 - **Mechanism:** Users deploy a Cloudflare Worker (VLESS-over-WS) and link it in the dashboard.
 - **Features:** Supports custom UUID input for authenticated workers.
 - **Benefit:** Clean IP reputation, zero cost for the platform.

 ## 4. Client-Side WASM Verification
 - **Objective:** "Residency-Based" testing.
 - **Mechanism:** A Go-based WASM module runs in the browser to test WebSocket proxies from the user's location.

 ## 5. Signed Subscription Integrity
 - **Objective:** Prevent MitM attacks.
 - **Implementation:** Ed25519 signatures attached to subscription files.
 - **Verification:** Client verifies signature against a hardcoded public key before loading.

 ## 6. Traffic Shapeshifting
 - **Objective:** Optimize multi-hop chains.
 - **Logic:** Geodesic distance calculation to ensure `Origin -> Relay -> Exit` is efficient.
