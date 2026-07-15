#!/usr/bin/env python3
"""从三套 SVG 源文件构建可直接替换的 Tauri 图标包。"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent
VARIANTS = ("core", "apex", "signal")
PNG_SIZES = (16, 32, 64, 128, 256, 512, 1024)
WINDOWS_SIZES = {
    "Square30x30Logo.png": 30,
    "Square44x44Logo.png": 44,
    "Square71x71Logo.png": 71,
    "Square89x89Logo.png": 89,
    "Square107x107Logo.png": 107,
    "Square142x142Logo.png": 142,
    "Square150x150Logo.png": 150,
    "Square284x284Logo.png": 284,
    "Square310x310Logo.png": 310,
    "StoreLogo.png": 50,
}


def run(*args: str) -> None:
    subprocess.run(args, check=True, stdin=subprocess.DEVNULL)


def render_svg(svg_path: Path, render_dir: Path) -> Path:
    render_dir.mkdir(parents=True, exist_ok=True)
    run("qlmanage", "-t", "-s", "1024", "-o", str(render_dir), str(svg_path))
    rendered = render_dir / f"{svg_path.name}.png"
    if not rendered.exists():
        raise FileNotFoundError(f"Quick Look 未生成预期文件: {rendered}")
    return rendered


def save_png(source: Image.Image, path: Path, size: int) -> None:
    resized = source.resize((size, size), Image.Resampling.LANCZOS)
    resized.save(path, format="PNG", optimize=True)


def build_variant(name: str) -> None:
    variant_dir = ROOT / "variants" / name
    tauri_dir = variant_dir / "tauri"
    iconset_dir = variant_dir / "icon.iconset"
    render_dir = variant_dir / ".rendered"
    tauri_dir.mkdir(parents=True, exist_ok=True)
    iconset_dir.mkdir(parents=True, exist_ok=True)

    rendered = render_svg(variant_dir / "app-icon.svg", render_dir)
    with Image.open(rendered) as image:
        source = image.convert("RGBA")
        if source.size != (1024, 1024):
            source = source.resize((1024, 1024), Image.Resampling.LANCZOS)

        for size in PNG_SIZES:
            save_png(source, tauri_dir / f"{size}x{size}.png", size)

        shutil.copy2(tauri_dir / "1024x1024.png", tauri_dir / "icon-source.png")
        shutil.copy2(tauri_dir / "512x512.png", tauri_dir / "icon.png")
        shutil.copy2(tauri_dir / "256x256.png", tauri_dir / "128x128@2x.png")

        for filename, size in WINDOWS_SIZES.items():
            save_png(source, tauri_dir / filename, size)

        ico_sizes = (16, 24, 32, 48, 64, 128, 256)
        source.save(
            tauri_dir / "icon.ico",
            format="ICO",
            sizes=[(size, size) for size in ico_sizes],
        )

        iconset_specs = {
            "icon_16x16.png": 16,
            "icon_16x16@2x.png": 32,
            "icon_32x32.png": 32,
            "icon_32x32@2x.png": 64,
            "icon_128x128.png": 128,
            "icon_128x128@2x.png": 256,
            "icon_256x256.png": 256,
            "icon_256x256@2x.png": 512,
            "icon_512x512.png": 512,
            "icon_512x512@2x.png": 1024,
        }
        for filename, size in iconset_specs.items():
            save_png(source, iconset_dir / filename, size)

    run("iconutil", "-c", "icns", str(iconset_dir), "-o", str(tauri_dir / "icon.icns"))


def main() -> None:
    for variant in VARIANTS:
        build_variant(variant)
        print(f"已生成: {variant}")


if __name__ == "__main__":
    main()
