#!/usr/bin/env python3
"""
Generate all favicons from logo SVG file

This script reads the logo SVG and generates favicons in multiple sizes:
- favicon.ico (16x16, 32x32, 48x48 multi-size ICO)
- favicon-16x16.png
- favicon-32x32.png
- favicon-48x48.png
- icon-192x192.png (PWA)
- icon-512x512.png (PWA)
- apple-touch-icon.png (180x180)
- apple-touch-icon-180x180.png (180x180)
"""

import sys
from pathlib import Path
from typing import List, Optional
from PIL import Image
import io

try:
    import cairosvg
except ImportError:
    print("ERROR: cairosvg not installed. Install with: pip install cairosvg")
    sys.exit(1)


def svg_to_png(svg_path: Path, output_path: Path, size: int) -> Optional[Image.Image]:
    """Convert SVG to PNG at specified size"""
    print(f"  Generating {output_path.name} ({size}x{size})...")

    try:
        # Convert SVG to PNG bytes
        png_data = cairosvg.svg2png(
            url=str(svg_path),
            output_width=size,
            output_height=size,
        )

        # Load PNG data into PIL Image
        img: Image.Image = Image.open(io.BytesIO(png_data))

        # Ensure RGBA mode
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        # Save PNG
        img.save(output_path, "PNG", optimize=True)
        print(f"    ✓ Created {output_path.name}")

        return img

    except Exception as e:
        print(f"    ✗ Failed to generate {output_path.name}: {e}")
        return None


def create_ico(
    svg_path: Path, output_path: Path, sizes: Optional[List[int]] = None
) -> None:
    """Create multi-size ICO file"""
    if sizes is None:
        sizes = [16, 32, 48]

    print(f"  Generating {output_path.name} (multi-size: {sizes})...")

    images: List[Image.Image] = []
    for size in sizes:
        try:
            png_data = cairosvg.svg2png(
                url=str(svg_path), output_width=size, output_height=size
            )
            img: Image.Image = Image.open(io.BytesIO(png_data))
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            images.append(img)
        except Exception as e:
            print(f"    ✗ Failed to generate {size}x{size} for ICO: {e}")
            continue

    if images:
        try:
            # Save as ICO with multiple sizes
            images[0].save(
                output_path,
                format="ICO",
                sizes=[(img.width, img.height) for img in images],
                append_images=images[1:],
            )
            print(f"    ✓ Created {output_path.name}")
        except Exception as e:
            print(f"    ✗ Failed to save ICO: {e}")
    else:
        print("    ✗ No images generated for ICO")


def main() -> None:
    """Main function to generate all favicons from logo SVG"""
    # Paths
    project_root = Path(__file__).parent.parent
    svg_path = project_root / "frontend" / "assets" / "svg" / "favicon.svg"
    output_dir = project_root / "frontend" / "assets" / "images"

    if not svg_path.exists():
        print(f"ERROR: SVG file not found: {svg_path}")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Generating Favicons from Logo SVG")
    print("=" * 60)
    print(f"Source: {svg_path}")
    print(f"Output: {output_dir}")
    print()

    # Generate standard favicons
    print("Generating PNG favicons...")
    svg_to_png(svg_path, output_dir / "favicon-16x16.png", 16)
    svg_to_png(svg_path, output_dir / "favicon-32x32.png", 32)
    svg_to_png(svg_path, output_dir / "favicon-48x48.png", 48)
    print()

    # Generate PWA icons
    print("Generating PWA icons...")
    svg_to_png(svg_path, output_dir / "icon-192x192.png", 192)
    svg_to_png(svg_path, output_dir / "icon-512x512.png", 512)
    print()

    # Generate Apple touch icons
    print("Generating Apple touch icons...")
    svg_to_png(svg_path, output_dir / "apple-touch-icon.png", 180)
    svg_to_png(svg_path, output_dir / "apple-touch-icon-180x180.png", 180)
    print()

    # Generate multi-size ICO
    print("Generating favicon.ico...")
    create_ico(svg_path, output_dir / "favicon.ico", [16, 32, 48])
    print()

    print("=" * 60)
    print("✅ Favicon generation complete!")
    print("=" * 60)
    print()
    print("Generated files:")
    for file in sorted(output_dir.glob("favicon*")):
        print(f"  - {file.name}")
    for file in sorted(output_dir.glob("icon-*")):
        print(f"  - {file.name}")
    for file in sorted(output_dir.glob("apple-touch-icon*")):
        print(f"  - {file.name}")


def generate_stealth_assets(output_dir):
    # Create a 1x1 transparent pixel or generic grey circle for stealth
    from PIL import Image, ImageDraw

    stealth_dir = output_dir / "stealth"
    stealth_dir.mkdir(exist_ok=True)

    # 1. Stealth Favicon (Grey Circle)
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((8, 8, 56, 56), fill="#808080")  # Generic grey dot
    img.save(stealth_dir / "favicon.ico", format="ICO")
    img.save(stealth_dir / "apple-touch-icon.png", format="PNG")

    # 2. Stealth Background (Solid muted color)
    bg = Image.new("RGB", (1920, 1080), "#f0f2f5")  # Generic office grey/white
    bg.save(stealth_dir / "background.png")

    print(f"    ✓ Generated Stealth Assets in {stealth_dir}")


if __name__ == "__main__":
    main()
    output_dir = Path(__file__).parent.parent / "frontend" / "assets" / "images"
    generate_stealth_assets(output_dir)
