# Firewalls & Honeypots

## The Great Firewall (GFW)
A blanket term for the censorship apparatus of China, but technically applicable to any state-level censorship system (Iran, Russia).
*   **DNS Poisoning:** Returning fake IP addresses for blocked domains (e.g., `google.com`).
*   **IP Blocking:** Blacklisting specific IP addresses.
*   **SNI Blocking:** Inspecting the TLS `Server Name Indication` field to block specific sites even on shared IPs.
*   **Active Probing:** The firewall acts like a "hacker". When it sees a suspicious connection (e.g., a Shadowsocks packet), it sends its own packets to the server to see if it responds like a proxy. If it does, the IP is banned.

## Honeypots
A honeypot is a trap set to detect, deflect, or counteract attempts at unauthorized use of information systems.
*   **Proxy Honeypots:** Malicious actors (or researchers) set up free, open proxies. When you connect, they log your traffic, IP, and destination.
*   **Detection:** ConfigStream actively avoids "suspicious" ports (like 22, 23, 445) and uses heuristic analysis to flag proxies that behave like honeypots (e.g., always returning success but passing no data).

## How ConfigStream Defends
1.  **Stealth Protocols:** We prioritize Reality/VLESS which look like normal HTTPS.
2.  **Clean IP Chaining:** We hide the true destination behind a clean relay.
3.  **Circuit Breakers:** If a server starts behaving oddly (random timeouts), we cut it off.
