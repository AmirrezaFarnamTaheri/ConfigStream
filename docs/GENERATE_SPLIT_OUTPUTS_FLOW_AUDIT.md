# Generate Split Outputs Flow Audit

## `generate_split_outputs` Execution Flowchart

```text
[ Start generate_split_outputs ]
       |
       v
[ 1. Init _base_outbound_cache ] ---> Pre-compile `to_singbox_outbound(p)` for non-chain proxies
       |
       +-------------------------------------------------------------+
       |                                                             |
       v                                                             v
[ 2. Sniper Generation ]                                     [ 3. Tank Generation ]
       |                                                             |
[ Resolve Chained Proxies ] <------------------------> [ Resolve Chained Proxies ]
       |                                                             |
[ Deepcopy Cache Payload  ]                          [ Deepcopy Cache Payload  ]
       |                                                             |
[ Apply EVASION_MODE      ] <-- Aggressive/Stealth   [ BYPASS EVASION (Clean)  ]
[ Mutate TLS/ALPN/Frag    ]                                          |
       |                                                             |
[ Merge Washed & Chains   ]                          [ Merge Washed & Chains   ]
       |                                                             |
[ Inject Sniper Groups    ]                          [ Inject Tank Groups      ]
[ (Auto, Fallback, etc)   ]                          [ (Washed, Intranet, Auto)]
       |                                                             |
[ Strip Internal Metadata ]                          [ Strip Internal Metadata ]
       |                                                             |
[ Add mixed inbound (2080)]                          [ Add tun inbound & route ]
       |                                                             |
[ Write singbox.json      ]                          [ Write singbox-vpn.json  ]
       |                                                             |
       +-----------------------------+-------------------------------+
                                     |
                                     v
                       [ 4. Clash Generation ]
                       [ Write clash.yaml    ]
                                     |
                                     v
                                  [ END ]
```

## Sniper vs Tank Outbound Configuration Audit Table

| Feature | Sniper Strategy (`singbox.json`) | Tank Strategy (`singbox-vpn.json`) |
| --- | --- | --- |
| **Inbound Mode** | `mixed` (listen: 127.0.0.1:2080) | `tun` (interface: tun0, auto/strict route) |
| **Evasion Strategy** | **Active.** Mutated based on `EVASION_MODE`. | **Clean.** Standard protocol payload. |
| **Fragmentation** | Yes, if aggressive/stealth (`get_fragment_config`) | No |
| **uTLS Fingerprint** | Yes, if aggressive/stealth (`rotate_tls_fingerprint`) | No |
| **ALPN Rotation** | Yes, if aggressive (`rotate_alpn`) | No |
| **Multiplexing** | Yes, if aggressive (`add_multiplexing`) | No |
| **TCP Fast Open** | Yes, if aggressive/stealth | No |
| **MPTCP** | Yes, if aggressive | No |
| **Group Selectors** | Auto, Proxy Select, Auto-Fallback, Mode Selector | Auto, Washed, Intranet, Proxy Select |
| **Base Configuration** | Cache Deepcopy -> Mutated | Cache Deepcopy -> Clean |

## Censorship Evasion & DNS Rule Set Insertion Audit

### Evasion Logic (`enrich_outbound_with_evasion`)
- **Deterministic Rotation**: Uses a time-seeded `_rotation_hash` bounded to `proxy_id`. This prevents aggressive mid-connection fingerprint swapping (which causes drops) while periodically cycling fingerprints to defeat active probing.
- **Mode Matrix**: 
  - `aggressive`: Active uTLS, ALPN rotation, Fragmentation, Multiplexing, TFO, MPTCP, and Padding.
  - `stealth`: Disables ALPN, Multiplexing, MPTCP, and Padding (reduces entropy signatures), but maintains uTLS and Fragmentation.
  - `standard`: Completely bypasses evasion injection.

### DNS & Rule Sets
- **DNS Profiles**: The `singbox_dns_profile` is securely deeply copied directly into the root level of both Tank and Sniper configurations.
- **Routing Rules**: Tank forces a `"protocol": "dns", "outbound": "dns-out"` rule out of the box to capture system DNS via the TUN interface and prevent DNS leaks outside the tunnel. Core required outbounds (`direct`, `block`, `dns-out`) are guaranteed to be appended if missing.

## Memory Reuse & Cache Efficiency Findings

### The Good
- **`_base_outbound_cache`**: Reduces redundant execution. `to_singbox_outbound` is only executed once per standard proxy instead of twice (Sniper + Tank).
- **Deep Copy Isolation**: Calling `copy.deepcopy` on the cached entry ensures that the heavy evasion mutations applied to the Sniper configuration do not taint the Tank configuration. Tank cleanly retrieves the unadulterated base proxy config.

### The Bad (Inefficiencies)
- **Chain Bypass**: Proxies containing chains (`chain_outbounds_from_details`) skip the caching layer. They are evaluated separately for both Sniper and Tank loops. Depending on the depth of `extract_chain_proxies`, this could invoke redundant serialization compute overhead.
- **Tag Suffixing Collision Loop**: The `while f"{tag}-{suffix}" in seen_tags:` iteration resolves collisions linearly. In a worst-case scenario with massive proxy lists having the same tag prefixes, this degrades to O(N^2) complexity.

## Recommended Code Improvements

1. **Memoize Chain Extraction**: Compute `chain_outbounds_from_details` in the initial `_base_outbound_cache` preparation loop. Store the chains in a secondary chain cache to avoid redundant node extractions in both the Sniper and Tank loops.
2. **Optimize Tag Uniquification**: Replace the `while f"{tag}-{suffix}" in seen_tags:` linear string-check loop with a dedicated `Dict[str, int]` collision counter map (e.g. `tag_counts[tag] += 1`). 
3. **Upstream Metadata Stripping**: The `_strip_internal_metadata` function runs a complete dictionary sweep at the very end of the outbound pipeline. Stripping metadata immediately inside `to_singbox_outbound` or the caching step would prevent carrying invalid keys through the deepcopy phases entirely.
