# SPDX-License-Identifier: AGPL-3.0-or-later
"""Generate the repository's self-contained architecture/README SVG assets."""

from __future__ import annotations

import html
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets"
LOGGER = logging.getLogger(__name__)

FONT = "system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif"
MONO = "ui-monospace,'SFMono-Regular',Consolas,monospace"
BG = "#090D16"
CARD = "#141E33"
BORDER = "#334155"
TEXT = "#F8FAFC"
MUTED = "#94A3B8"
CYAN = "#06B6D4"
VIOLET = "#8B5CF6"
EMERALD = "#10B981"
AMBER = "#F59E0B"
ROSE = "#F43F5E"


def _write_svg(name: str, body: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    target = OUT_DIR / name
    target.write_text(body.strip() + "\n", encoding="utf-8")
    LOGGER.info("wrote %-16s %6d B", name, target.stat().st_size)


def _base_svg(width: int, height: int, title: str, content: str) -> str:
    safe_title = html.escape(title)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="{safe_title}">
  <title>{safe_title}</title>
  <rect width="{width}" height="{height}" rx="14" fill="{BG}"/>
  <rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="13" fill="none" stroke="{BORDER}"/>
  {content}
</svg>"""


def generate_hero() -> None:
    chips = ["VLESS", "VMess", "Trojan", "Shadowsocks", "Hysteria2", "TUIC", "MASQUE", "WARP"]
    chip_markup: list[str] = []
    x = 50
    for label in chips:
        safe = html.escape(label)
        chip_markup.append(
            f'<g transform="translate({x},220)"><rect width="135" height="46" rx="8" fill="{CARD}" stroke="{BORDER}"/>'
            f'<circle cx="17" cy="23" r="4" fill="{CYAN}"><animate attributeName="opacity" values=".35;1;.35" dur="2s" repeatCount="indefinite"/></circle>'
            f'<text x="31" y="28" font-family="{MONO}" font-size="11" fill="{TEXT}">{safe}</text></g>'
        )
        x += 145
    content = f"""
  <circle cx="92" cy="58" r="6" fill="{EMERALD}"><animate attributeName="r" values="6;12;6" dur="2.4s" repeatCount="indefinite"/></circle>
  <text x="112" y="63" font-family="{MONO}" font-size="12" fill="{EMERALD}">SYSTEM STATUS: OPERATIONAL</text>
  <text x="50" y="132" font-family="{FONT}" font-size="46" font-weight="800" fill="{TEXT}">ConfigStream</text>
  <text x="50" y="170" font-family="{FONT}" font-size="17" fill="{MUTED}">Validated multi-protocol ingestion, testing, washing, and distribution</text>
  <line x1="50" y1="192" x2="1230" y2="192" stroke="{CYAN}" stroke-opacity=".65"/>
  {''.join(chip_markup)}
"""
    _write_svg("hero.svg", _base_svg(1280, 300, "ConfigStream telemetry banner", content))


def generate_pipeline() -> None:
    stages = [
        ("01", "INGESTION", CYAN),
        ("02", "ADMISSION", VIOLET),
        ("03", "VERIFICATION", EMERALD),
        ("04", "WASHING", AMBER),
        ("05", "DISTRIBUTION", ROSE),
    ]
    blocks: list[str] = []
    x = 35
    for index, (number, label, color) in enumerate(stages):
        blocks.append(
            f'<g transform="translate({x},35)"><rect width="210" height="105" rx="10" fill="{CARD}" stroke="{color}"/>'
            f'<text x="16" y="28" font-family="{MONO}" font-size="11" fill="{color}">{number}</text>'
            f'<text x="16" y="58" font-family="{FONT}" font-size="15" font-weight="700" fill="{TEXT}">{html.escape(label)}</text>'
            f'<text x="16" y="84" font-family="{FONT}" font-size="11" fill="{MUTED}">validated stage</text></g>'
        )
        if index < len(stages) - 1:
            blocks.append(
                f'<line x1="{x + 210}" y1="87" x2="{x + 245}" y2="87" stroke="{BORDER}" stroke-width="2"/>'
                f'<circle cy="87" r="3" fill="{color}"><animate attributeName="cx" values="{x + 214};{x + 241};{x + 214}" dur="1.7s" repeatCount="indefinite"/></circle>'
            )
        x += 245
    _write_svg(
        "pipeline.svg",
        _base_svg(1280, 180, "ConfigStream five-stage pipeline", "\n".join(blocks)),
    )


def generate_divider() -> None:
    content = f"""
  <line x1="25" y1="10" x2="1255" y2="10" stroke="{CYAN}" stroke-opacity=".55"/>
  <polygon points="640,3 647,10 640,17 633,10" fill="{CYAN}">
    <animateTransform attributeName="transform" type="rotate" from="0 640 10" to="360 640 10" dur="8s" repeatCount="indefinite"/>
  </polygon>
"""
    _write_svg("divider.svg", _base_svg(1280, 20, "ConfigStream section divider", content))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    LOGGER.info("Generating SVG assets in %s", OUT_DIR)
    generate_hero()
    generate_pipeline()
    generate_divider()
    LOGGER.info("SVG asset generation complete")


if __name__ == "__main__":
    main()
