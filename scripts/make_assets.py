# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Generates self-contained, high-fidelity SVG assets for ConfigStream README & Docs.
Renders natively on BOTH light and dark GitHub themes without external CDNs.
Uses pure SMIL (<animate>) which is preserved by GitHub's Camo image proxy.
Designed according to modern Cyber-Minimalist & Precision Telemetry standards.
All XML text is strictly escaped (&amp;, &lt;, &gt;) for 100% SVG/XML compliance.
"""

from __future__ import annotations

import html
from pathlib import Path

OUT_DIR = Path("assets")
FONT = "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
MONO = "'JetBrains Mono', 'SF Mono', Consolas, Menlo, Monaco, monospace"

# Color Palette (High-Contrast Cyberpunk & Slate Palette)
BG_DARK = "#060A12"
BG_SURFACE = "#0C1322"
BG_CARD = "#111B30"
BORDER = "#1E2C4A"
BORDER_BRIGHT = "#334B75"

TEXT_WHITE = "#FFFFFF"
TEXT_SLATE_100 = "#F1F5F9"
TEXT_SLATE_400 = "#94A3B8"
TEXT_SLATE_500 = "#64748B"

CYAN = "#00E5FF"
CYAN_DIM = "#0891B2"
VIOLET = "#A855F7"
EMERALD = "#10B981"
AMBER = "#F59E0B"
ROSE = "#FB7185"
BLUE = "#38BDF8"


def write_svg(name: str, body: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    target = OUT_DIR / name
    target.write_text(body.strip() + "\n", encoding="utf-8")
    print(f"  wrote {name:22s} {target.stat().st_size:6d} B")


def _build_hero_chips() -> str:
    chips = [
        ("VLESS", CYAN, "XTLS / Reality"),
        ("VMess", BLUE, "AEAD / WS"),
        ("Trojan", EMERALD, "gRPC / TLS"),
        ("Shadowsocks", AMBER, "2022-blake3"),
        ("Hysteria2", ROSE, "Brutal UDP"),
        ("TUIC", VIOLET, "QUIC / BBR"),
        ("MASQUE", CYAN, "HTTP/3 Proxy"),
        ("WARP", EMERALD, "Dual-Stack"),
    ]
    cx = 50
    chip_svgs = []
    for label, col, sub in chips:
        cw = 138
        esc_label = html.escape(label)
        esc_sub = html.escape(sub)
        chip_svgs.append(
            f'<g transform="translate({cx}, 224)">'
            f'<rect width="{cw}" height="48" rx="8" fill="{BG_CARD}" stroke="{col}" stroke-width="1.2" stroke-opacity="0.6"/>'
            f'<circle cx="16" cy="24" r="3.5" fill="{col}">'
            f'<animate attributeName="opacity" values="0.4;1;0.4" dur="2s" repeatCount="indefinite"/>'
            f"</circle>"
            f'<text x="28" y="21" font-family="{FONT}" font-size="13" font-weight="700" fill="{TEXT_WHITE}" letter-spacing="0.3">{esc_label}</text>'
            f'<text x="28" y="36" font-family="{MONO}" font-size="9.5" font-weight="500" fill="{TEXT_SLATE_400}">{esc_sub}</text>'
            f"</g>"
        )
        cx += cw + 10
    return "".join(chip_svgs)


def generate_hero() -> None:
    w, h = 1280, 300
    chip_markup = _build_hero_chips()

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="ConfigStream Hero Banner">
  <title>ConfigStream — Sovereign-Grade Anti-Censorship Aggregation Platform</title>
  <defs>
    <!-- Background Gradients -->
    <linearGradient id="hbg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{BG_DARK}"/>
      <stop offset="50%" stop-color="{BG_SURFACE}"/>
      <stop offset="100%" stop-color="{BG_DARK}"/>
    </linearGradient>
    <radialGradient id="haura1" cx="20%" cy="30%" r="50%">
      <stop offset="0%" stop-color="{CYAN}" stop-opacity="0.18"/>
      <stop offset="100%" stop-color="{CYAN}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="haura2" cx="80%" cy="70%" r="50%">
      <stop offset="0%" stop-color="{VIOLET}" stop-opacity="0.15"/>
      <stop offset="100%" stop-color="{VIOLET}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="laserLine" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{CYAN}" stop-opacity="0"/>
      <stop offset="30%" stop-color="{CYAN}" stop-opacity="0.8"/>
      <stop offset="70%" stop-color="{VIOLET}" stop-opacity="0.8"/>
      <stop offset="100%" stop-color="{VIOLET}" stop-opacity="0"/>
    </linearGradient>
    <!-- Grid Pattern -->
    <pattern id="hgrid" width="32" height="32" patternUnits="userSpaceOnUse">
      <path d="M 32 0 L 0 0 0 32" fill="none" stroke="{BORDER}" stroke-width="0.75" stroke-opacity="0.4"/>
      <circle cx="1" cy="1" r="1" fill="{TEXT_SLATE_500}" fill-opacity="0.25"/>
    </pattern>
    <clipPath id="hcard"><rect x="0" y="0" width="{w}" height="{h}" rx="14"/></clipPath>
  </defs>

  <g clip-path="url(#hcard)">
    <!-- Base Layer &amp; Grid -->
    <rect width="{w}" height="{h}" fill="url(#hbg)"/>
    <rect width="{w}" height="{h}" fill="url(#hgrid)"/>

    <!-- Subtle Dynamic Auroras -->
    <ellipse cx="280" cy="100" rx="420" ry="240" fill="url(#haura1)">
      <animate attributeName="cx" values="280;420;280" dur="12s" repeatCount="indefinite"/>
    </ellipse>
    <ellipse cx="1000" cy="200" rx="400" ry="220" fill="url(#haura2)">
      <animate attributeName="cx" values="1000;860;1000" dur="14s" repeatCount="indefinite"/>
    </ellipse>

    <!-- Outer Card Border -->
    <rect x="0.75" y="0.75" width="{w-1.5}" height="{h-1.5}" rx="14" fill="none" stroke="{BORDER_BRIGHT}" stroke-width="1.5"/>

    <!-- Top Status HUD Bar -->
    <rect x="50" y="24" width="380" height="28" rx="6" fill="{BG_CARD}" stroke="{BORDER}" stroke-width="1"/>
    <circle cx="66" cy="38" r="4.5" fill="{EMERALD}"/>
    <circle cx="66" cy="38" r="4.5" fill="none" stroke="{EMERALD}" stroke-width="1.5">
      <animate attributeName="r" values="4.5;14;4.5" dur="2.2s" repeatCount="indefinite"/>
      <animate attributeName="opacity" values="0.8;0;0.8" dur="2.2s" repeatCount="indefinite"/>
    </circle>
    <text x="82" y="42" font-family="{MONO}" font-size="11" font-weight="600" fill="{EMERALD}" letter-spacing="0.5">
      SYSTEM STATUS: OPERATIONAL
    </text>
    <text x="270" y="42" font-family="{MONO}" font-size="11" font-weight="500" fill="{TEXT_SLATE_400}">
      | ZERO-TRUST PIPELINE
    </text>

    <!-- Telemetry Badges Right -->
    <g transform="translate(850, 24)">
      <rect width="180" height="28" rx="6" fill="{BG_CARD}" stroke="{BORDER}" stroke-width="1"/>
      <text x="18" y="18" font-family="{MONO}" font-size="11" font-weight="600" fill="{CYAN}">INGESTION:</text>
      <text x="96" y="18" font-family="{MONO}" font-size="11" font-weight="500" fill="{TEXT_WHITE}">CONTINUOUS</text>
    </g>
    <g transform="translate(1040, 24)">
      <rect width="190" height="28" rx="6" fill="{BG_CARD}" stroke="{BORDER}" stroke-width="1"/>
      <text x="18" y="18" font-family="{MONO}" font-size="11" font-weight="600" fill="{VIOLET}">VERIFICATION:</text>
      <text x="114" y="18" font-family="{MONO}" font-size="11" font-weight="500" fill="{TEXT_WHITE}">GO SUB-MS</text>
    </g>

    <!-- Main Branding -->
    <text x="50" y="112" font-family="{FONT}" font-size="44" font-weight="800" fill="{TEXT_WHITE}" letter-spacing="-1">
      ConfigStream
    </text>
    <text x="356" y="96" font-family="{MONO}" font-size="12" font-weight="700" fill="{CYAN}" letter-spacing="1">
      v3.2.0-ENTERPRISE
    </text>

    <!-- Glowing Accent Accent Bar -->
    <path d="M 50 128 L 680 128" stroke="url(#laserLine)" stroke-width="2.5"/>

    <!-- Subtitle &amp; Value Proposition -->
    <text x="50" y="158" font-family="{FONT}" font-size="18" font-weight="600" fill="{TEXT_SLATE_100}" letter-spacing="-0.2">
      Sovereignty-Grade Anti-Censorship Aggregator &amp; Autonomous Multi-Tier Stream Washer
    </text>
    <text x="50" y="186" font-family="{FONT}" font-size="13.5" font-weight="400" fill="{TEXT_SLATE_400}">
      SSRF-Guarded Ingestion • Native Sing-box Testing • WARP/MASQUE Chaining • Subscriptions for Hiddify &amp; Clash Verge
    </text>

    <!-- Protocol Badges Matrix -->
    {chip_markup}
  </g>
</svg>"""
    write_svg("hero.svg", svg)


def _build_pipeline_stages() -> str:
    stages = [
        ("01", "INGESTION", "Git, Telegram, HTTP Feeds", CYAN, "10,000+ Raw"),
        ("02", "ADMISSION", "SSRF Guard & AST Dedupe", VIOLET, "Zero-Trust Safe"),
        ("03", "VERIFICATION", "Go Fast TCP & HTTP/204", EMERALD, "< 120ms Latency"),
        ("04", "STREAM WASHER", "WARP & MASQUE Chains", AMBER, "100% Unblocked"),
        ("05", "DISTRIBUTION", "Clash, Sing-box, B64", ROSE, "Universal CDN"),
    ]
    sw = 216
    gap = 26
    start_x = 42
    stage_svgs = []

    for i, (num, title, desc, col, metric) in enumerate(stages):
        x = start_x + i * (sw + gap)
        esc_title = html.escape(title)
        esc_desc = html.escape(desc)
        esc_metric = html.escape(metric)
        stage_svgs.append(
            f'<g transform="translate({x}, 32)">'
            f'<rect width="{sw}" height="114" rx="10" fill="{BG_CARD}" stroke="{col}" stroke-width="1.2" stroke-opacity="0.65"/>'
            f"<!-- Header Pill -->"
            f'<rect x="12" y="12" width="30" height="18" rx="4" fill="{col}" fill-opacity="0.15" stroke="{col}" stroke-width="1"/>'
            f'<text x="27" y="25" text-anchor="middle" font-family="{MONO}" font-size="10" font-weight="700" fill="{col}">{num}</text>'
            f'<text x="50" y="26" font-family="{FONT}" font-size="13.5" font-weight="700" fill="{TEXT_WHITE}" letter-spacing="0.2">{esc_title}</text>'
            f"<!-- Description -->"
            f'<text x="12" y="58" font-family="{FONT}" font-size="11.5" font-weight="400" fill="{TEXT_SLATE_400}">{esc_desc}</text>'
            f"<!-- Divider Line -->"
            f'<line x1="12" y1="74" x2="{sw-12}" y2="74" stroke="{BORDER}" stroke-width="1"/>'
            f"<!-- Metric Tag -->"
            f'<circle cx="20" cy="92" r="3" fill="{col}"/>'
            f'<text x="30" y="96" font-family="{MONO}" font-size="10.5" font-weight="600" fill="{col}">{esc_metric}</text>'
            f"</g>"
        )

        if i < len(stages) - 1:
            ax = x + sw + 3
            stage_svgs.append(
                f'<g transform="translate({ax}, 89)">'
                f'<line x1="0" y1="0" x2="{gap - 6}" y2="0" stroke="{BORDER_BRIGHT}" stroke-width="2" stroke-dasharray="3 3"/>'
                f'<polygon points="{gap-6},0 {gap-12},-3.5 {gap-12},3.5" fill="{col}"/>'
                f'<circle cx="10" cy="0" r="3.5" fill="{col}">'
                f'<animate attributeName="cx" values="2;{gap-8};2" dur="1.8s" repeatCount="indefinite"/>'
                f'<animate attributeName="opacity" values="0.2;1;0.2" dur="1.8s" repeatCount="indefinite"/>'
                f"</circle>"
                f"</g>"
            )
    return "".join(stage_svgs)


def generate_pipeline() -> None:
    w, h = 1280, 180
    stage_markup = _build_pipeline_stages()

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="ConfigStream Multi-Stage Pipeline">
  <title>ConfigStream — 5-Stage Verification &amp; Distribution Pipeline</title>
  <defs>
    <linearGradient id="pbg" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{BG_DARK}"/>
      <stop offset="50%" stop-color="{BG_SURFACE}"/>
      <stop offset="100%" stop-color="{BG_DARK}"/>
    </linearGradient>
    <pattern id="pgrid" width="24" height="24" patternUnits="userSpaceOnUse">
      <circle cx="1" cy="1" r="0.75" fill="{TEXT_SLATE_500}" fill-opacity="0.2"/>
    </pattern>
    <clipPath id="pcard"><rect x="0" y="0" width="{w}" height="{h}" rx="12"/></clipPath>
  </defs>

  <g clip-path="url(#pcard)">
    <rect width="{w}" height="{h}" fill="url(#pbg)"/>
    <rect width="{w}" height="{h}" fill="url(#pgrid)"/>
    <rect x="0.75" y="0.75" width="{w-1.5}" height="{h-1.5}" rx="12" fill="none" stroke="{BORDER_BRIGHT}" stroke-width="1.5"/>

    <!-- Pipeline Stages -->
    {stage_markup}
  </g>
</svg>"""
    write_svg("pipeline.svg", svg)


def generate_divider() -> None:
    w, h = 1280, 20
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="ConfigStream Divider">
  <defs>
    <linearGradient id="divLaser" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{BG_DARK}" stop-opacity="0"/>
      <stop offset="25%" stop-color="{CYAN}" stop-opacity="0.3"/>
      <stop offset="50%" stop-color="{CYAN}" stop-opacity="0.9"/>
      <stop offset="75%" stop-color="{VIOLET}" stop-opacity="0.3"/>
      <stop offset="100%" stop-color="{BG_DARK}" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="coreGlow" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{CYAN}" stop-opacity="0"/>
      <stop offset="50%" stop-color="#FFFFFF" stop-opacity="1"/>
      <stop offset="100%" stop-color="{VIOLET}" stop-opacity="0"/>
    </linearGradient>
  </defs>

  <!-- Base Laser Line -->
  <line x1="80" y1="10" x2="1200" y2="10" stroke="url(#divLaser)" stroke-width="1.5"/>
  <line x1="440" y1="10" x2="840" y2="10" stroke="url(#coreGlow)" stroke-width="2"/>

  <!-- Center Diamond Crosshair -->
  <g transform="translate(640, 10)">
    <polygon points="0,-6 6,0 0,6 -6,0" fill="{CYAN}">
      <animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="8s" repeatCount="indefinite"/>
    </polygon>
    <circle cx="0" cy="0" r="2.5" fill="#FFFFFF"/>
    <circle cx="0" cy="0" r="8" fill="none" stroke="{CYAN}" stroke-width="1" stroke-opacity="0.5">
      <animate attributeName="r" values="6;12;6" dur="2.5s" repeatCount="indefinite"/>
      <animate attributeName="opacity" values="0.8;0.1;0.8" dur="2.5s" repeatCount="indefinite"/>
    </circle>
  </g>

  <!-- Traveling Photon Packet -->
  <circle cy="10" r="3" fill="{CYAN}">
    <animate attributeName="cx" values="180;1100;180" dur="5s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values="0.3;1;0.3" dur="5s" repeatCount="indefinite"/>
  </circle>
</svg>"""
    write_svg("divider.svg", svg)


def main() -> None:
    print("Generating precision cyber-minimalist SVG assets...")
    generate_hero()
    generate_pipeline()
    generate_divider()
    print("All assets generated successfully in assets/!")


if __name__ == "__main__":
    main()
