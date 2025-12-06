# Security & Obfuscation Concepts

## Steganographic (Steganography)
From Greek *steganos* (covered) and *graphein* (writing). Unlike cryptography, which hides the *meaning* of a message, steganography hides the *existence* of the message.
*   **In ConfigStream:** We embed encrypted JSON configurations inside the Least Significant Bits (LSB) of JPEG/PNG images.
*   **Why?** A network administrator seeing you download `config.json` might block it. Seeing you download `cute_cat.jpg` is usually ignored.
*   **Transport:** The image acts as a "carrier" for the data.

## VirusTotal Integration
VirusTotal is a service that analyzes files and URLs using over 70 antivirus scanners.
*   **Role in ConfigStream:** Before including a proxy in our final list, we (optionally) check its IP or domain against VirusTotal's API.
*   **Safety:** This ensures we aren't distributing proxies hosted on known malware command-and-control (C2) servers, protecting users from malicious endpoints.

## Handshake
The initial negotiation phase of a network connection.
*   **The Vulnerability:** Censors (like the GFW) heavily inspect handshakes because they must be unencrypted (or partially unencrypted) to establish keys.
*   **WireGuard Handshake:** Very distinct 148-byte packet. Easy to block.
*   **Shadowsocks Handshake:** Originally random-looking, but machine learning can now detect its entropy profile.
*   **Reality Handshake:** Indistinguishable from a standard TLS handshake with a legitimate website.
