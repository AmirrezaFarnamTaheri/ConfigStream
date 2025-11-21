#!/usr/bin/env python3
"""
Generate favicons from the project logo SVG.
Creates multiple sizes for different use cases.
"""

import os
from pathlib import Path
import cairosvg
from PIL import Image
import io


def generate_favicon_png(svg_path: str, output_path: str, size: int):
    """Generate a PNG favicon from SVG at specified size."""
    print(f"Generating {size}x{size} PNG: {output_path}")

    # Convert SVG to PNG using cairosvg
    png_data = cairosvg.svg2png(url=svg_path, output_width=size, output_height=size)

    # Save the PNG
    with open(output_path, "wb") as f:
        f.write(png_data)


def generate_ico(svg_path: str, output_path: str):
    """Generate a multi-resolution ICO file from SVG."""
    print(f"Generating ICO: {output_path}")

    # Generate multiple sizes for ICO
    sizes = [16, 32, 48]
    images = []

    for size in sizes:
        png_data = cairosvg.svg2png(url=svg_path, output_width=size, output_height=size)
        img = Image.open(io.BytesIO(png_data))
        images.append(img)

    # Save as ICO with multiple resolutions
    images[0].save(
        output_path,
        format="ICO",
        sizes=[(img.width, img.height) for img in images],
        append_images=images[1:],
    )


def main():
    """Main function to generate all favicons."""
    # Paths
    project_root = Path(__file__).parent
    svg_logo = project_root / "frontend" / "assets" / "svg" / "favicon.svg"
    output_dir = project_root / "frontend" / "assets" / "images"

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Using logo: {svg_logo}")
    print(f"Output directory: {output_dir}")
    print()

    # Generate standard favicon sizes
    generate_favicon_png(str(svg_logo), str(output_dir / "favicon-16x16.png"), 16)
    generate_favicon_png(str(svg_logo), str(output_dir / "favicon-32x32.png"), 32)
    generate_favicon_png(str(svg_logo), str(output_dir / "favicon-48x48.png"), 48)

    # Generate Apple Touch Icons
    generate_favicon_png(str(svg_logo), str(output_dir / "apple-touch-icon.png"), 180)
    generate_favicon_png(
        str(svg_logo), str(output_dir / "apple-touch-icon-180x180.png"), 180
    )

    # Generate PWA icons
    generate_favicon_png(str(svg_logo), str(output_dir / "icon-192x192.png"), 192)
    generate_favicon_png(str(svg_logo), str(output_dir / "icon-512x512.png"), 512)

    # Generate multi-resolution ICO file
    generate_ico(str(svg_logo), str(output_dir / "favicon.ico"))

    print()
    print("✓ All favicons generated successfully!")


if __name__ == "__main__":
    main()
