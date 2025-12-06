# About Page Documentation

The **About** page serves as the project's manifesto and credits section. It explains the "Why" and "Who" behind ConfigStream.

## Design Philosophy: "Zero to Hero"

The page reflects the core values of the project: transparency, resilience, and community. It is text-heavy but structured for readability.

### Sections

#### 1. The Mission
*   Explains the goal of "Unstoppable Access".
*   Defines the problem (Internet Censorship) and the solution (Automated Aggregation).

#### 2. The Architecture (Simplified)
*   A high-level diagram or description of how the system works:
    *   GitHub Actions (The Engine) -> GitHub Pages (The CDN) -> User (The Beneficiary).
*   Explains the "Zero Budget" concept.

#### 3. Client Compatibility
*   Lists all supported client applications with links to their official download pages:
    *   **Android**: v2rayNG, Sing-box, Clash Meta.
    *   **iOS**: Shadowrocket, Stash, Quantumult X, Loon, Surge.
    *   **Desktop**: v2rayN, Clash Verge, Hiddify.

#### 4. Legal & Disclaimer
*   **No Logs Policy**: Reiteration that we do not and cannot store user data.
*   **Usage Warning**: ConfigStream is for educational and research purposes. Users are responsible for complying with their local laws.
*   **"As Is" Warranty**: No guarantees of uptime or speed.

#### 5. Credits & Resources
*   Links to the GitHub Repository.
*   Credits to open-source libraries used (Sing-box, geoip2, globe.gl, etc.).
*   Contact/Issues link for reporting bugs.

## Technical Implementation

*   **Static Content**: Pure HTML/CSS.
*   **Versioning**: Dynamically displays the current version of the ConfigStream CLI/Pipeline derived from the latest metadata.
