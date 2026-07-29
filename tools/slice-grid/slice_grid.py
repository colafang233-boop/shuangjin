#!/usr/bin/env python3
"""Split generated RPG asset boards into traceable individual assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from PIL import Image, ImageDraw, ImageOps


class SliceGridError(ValueError):
    """Raised when slicing parameters or source data are invalid."""


@dataclass(frozen=True)
class Edges:
    top: int = 0
    right: int = 0
    bottom: int = 0
    left: int = 0


@dataclass(frozen=True)
class Pair:
    x: int = 0
    y: int = 0


def parse_edges(value: str | int) -> Edges:
    """Parse CSS-like edge syntax: N, V,H, T,H,B, or T,R,B,L."""
    if isinstance(value, int):
        values = [value]
    else:
        try:
            values = [int(part.strip()) for part in str(value).split(",")]
        except ValueError as exc:
            raise argparse.ArgumentTypeError("边距必须是整数或逗号分隔整数") from exc
    if any(item < 0 for item in values):
        raise argparse.ArgumentTypeError("边距不能为负数")
    if len(values) == 1:
        return Edges(*(values * 4))
    if len(values) == 2:
        vertical, horizontal = values
        return Edges(vertical, horizontal, vertical, horizontal)
    if len(values) == 3:
        top, horizontal, bottom = values
        return Edges(top, horizontal, bottom, horizontal)
    if len(values) == 4:
        return Edges(*values)
    raise argparse.ArgumentTypeError("边距格式应为 N、V,H、T,H,B 或 T,R,B,L")


def parse_pair(value: str | int) -> Pair:
    if isinstance(value, int):
        return Pair(value, value)
    try:
        values = [int(part.strip()) for part in str(value).split(",")]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("间距必须是整数或 X,Y") from exc
    if any(item < 0 for item in values):
        raise argparse.ArgumentTypeError("间距不能为负数")
    if len(values) == 1:
        return Pair(values[0], values[0])
    if len(values) == 2:
        return Pair(values[0], values[1])
    raise argparse.ArgumentTypeError("间距格式应为 N 或 X,Y")


def parse_size(value: str) -> tuple[int, int]:
    match = re.fullmatch(r"\s*(\d+)\s*[xX×]\s*(\d+)\s*", value)
    if not match:
        raise argparse.ArgumentTypeError("画布尺寸格式应为 WIDTHxHEIGHT，例如 256x256")
    width, height = (int(match.group(1)), int(match.group(2)))
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError("画布尺寸必须大于零")
    return width, height


def row_label(index: int) -> str:
    if index < 0:
        raise ValueError("row index cannot be negative")
    result = ""
    value = index + 1
    while value:
        value, remainder = divmod(value - 1, 26)
        result = chr(ord("a") + remainder) + result
    return result


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def cell_box(
    image_size: tuple[int, int],
    rows: int,
    cols: int,
    row: int,
    col: int,
    margin: Edges,
    gutter: Pair,
) -> tuple[int, int, int, int]:
    width, height = image_size
    usable_width = width - margin.left - margin.right - gutter.x * (cols - 1)
    usable_height = height - margin.top - margin.bottom - gutter.y * (rows - 1)
    if usable_width <= 0 or usable_height <= 0:
        raise SliceGridError("边距和格间距超过了图片可用尺寸")

    cell_width = usable_width / cols
    cell_height = usable_height / rows
    left = margin.left + round(col * cell_width) + col * gutter.x
    right = margin.left + round((col + 1) * cell_width) + col * gutter.x
    top = margin.top + round(row * cell_height) + row * gutter.y
    bottom = margin.top + round((row + 1) * cell_height) + row * gutter.y
    if right <= left or bottom <= top:
        raise SliceGridError(f"格子 {row_label(row)}{col + 1} 的裁剪范围无效")
    return left, top, right, bottom


def trim_alpha(image: Image.Image, threshold: int) -> tuple[Image.Image, tuple[int, int, int, int] | None]:
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    mask = alpha.point(lambda value: 255 if value > threshold else 0)
    bbox = mask.getbbox()
    if bbox is None:
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0)), None
    return rgba.crop(bbox), bbox


def place_on_canvas(
    image: Image.Image,
    canvas_size: tuple[int, int],
    anchor: str,
) -> tuple[Image.Image, tuple[int, int]]:
    canvas_width, canvas_height = canvas_size
    if image.width > canvas_width or image.height > canvas_height:
        raise SliceGridError(
            f"裁剪结果 {image.width}x{image.height} 大于目标画布 {canvas_width}x{canvas_height}"
        )
    if anchor == "center":
        x = (canvas_width - image.width) // 2
        y = (canvas_height - image.height) // 2
    elif anchor == "bottom-center":
        x = (canvas_width - image.width) // 2
        y = canvas_height - image.height
    elif anchor == "top-left":
        x = 0
        y = 0
    else:
        raise SliceGridError(f"未知锚点：{anchor}")
    canvas = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    canvas.alpha_composite(image.convert("RGBA"), (x, y))
    return canvas, (x, y)


def save_image(image: Image.Image, path: Path, output_format: str) -> None:
    if output_format == "png":
        image.save(path, format="PNG", optimize=True)
    elif output_format == "webp":
        image.save(path, format="WEBP", lossless=True, method=6)
    else:
        raise SliceGridError(f"不支持的输出格式：{output_format}")


def make_contact_sheet(
    items: Sequence[dict],
    output_path: Path,
    thumb_size: int = 180,
    columns: int | None = None,
) -> None:
    if not items:
        raise SliceGridError("没有可生成联系表的素材")
    columns = columns or min(4, len(items))
    rows = math.ceil(len(items) / columns)
    label_height = 28
    gap = 12
    cell_width = thumb_size + gap * 2
    cell_height = thumb_size + label_height + gap * 2
    sheet = Image.new("RGB", (columns * cell_width, rows * cell_height), (22, 30, 38))
    draw = ImageDraw.Draw(sheet)

    for index, item in enumerate(items):
        row, col = divmod(index, columns)
        origin_x = col * cell_width + gap
        origin_y = row * cell_height + gap
        with Image.open(item["absolutePath"]) as source:
            preview = source.convert("RGBA")
            preview.thumbnail((thumb_size, thumb_size), Image.Resampling.LANCZOS)
            checker = Image.new("RGBA", (thumb_size, thumb_size), (42, 54, 64, 255))
            tile = 12
            checker_draw = ImageDraw.Draw(checker)
            for cy in range(0, thumb_size, tile):
                for cx in range(0, thumb_size, tile):
                    if (cx // tile + cy // tile) % 2:
                        checker_draw.rectangle((cx, cy, cx + tile - 1, cy + tile - 1), fill=(54, 68, 78, 255))
            px = (thumb_size - preview.width) // 2
            py = (thumb_size - preview.height) // 2
            checker.alpha_composite(preview, (px, py))
            sheet.paste(checker.convert("RGB"), (origin_x, origin_y))
        draw.text((origin_x, origin_y + thumb_size + 7), item["cell"], fill=(214, 238, 248))
        draw.text((origin_x + 34, origin_y + thumb_size + 7), item["filename"], fill=(145, 169, 180))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, format="PNG", optimize=True)


def slice_board(
    input_path: Path,
    output_dir: Path,
    *,
    rows: int,
    cols: int,
    margin: Edges = Edges(),
    gutter: Pair = Pair(),
    prefix: str | None = None,
    output_format: str = "png",
    trim: bool = False,
    trim_threshold: int = 4,
    padding: int = 0,
    canvas_size: tuple[int, int] | None = None,
    anchor: str = "center",
    overwrite: bool = False,
    manifest_path: Path | None = None,
    contact_sheet_path: Path | None = None,
) -> dict:
    if rows <= 0 or cols <= 0:
        raise SliceGridError("行列数必须大于零")
    if not 0 <= trim_threshold <= 255:
        raise SliceGridError("透明阈值必须在 0–255 之间")
    if padding < 0:
        raise SliceGridError("内边距不能为负数")
    if not input_path.is_file():
        raise SliceGridError(f"找不到输入图片：{input_path}")

    prefix = prefix or input_path.stem
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", prefix):
        raise SliceGridError("文件前缀只能包含英文、数字、下划线和连字符")
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_path or output_dir / f"{prefix}.manifest.json"
    if manifest_path.exists() and not overwrite:
        raise SliceGridError(f"Manifest 已存在：{manifest_path}；使用 --overwrite 覆盖")
    if contact_sheet_path and contact_sheet_path.exists() and not overwrite:
        raise SliceGridError(f"联系表已存在：{contact_sheet_path}；使用 --overwrite 覆盖")

    with Image.open(input_path) as source_image:
        source = source_image.convert("RGBA")
        items: list[dict] = []
        for row in range(rows):
            for col in range(cols):
                cell = f"{row_label(row)}{col + 1}"
                filename = f"{prefix}_{cell}.{output_format}"
                output_path = output_dir / filename
                if output_path.exists() and not overwrite:
                    raise SliceGridError(f"输出文件已存在：{output_path}；使用 --overwrite 覆盖")

        for row in range(rows):
            for col in range(cols):
                cell = f"{row_label(row)}{col + 1}"
                crop_box = cell_box(source.size, rows, cols, row, col, margin, gutter)
                cell_image = source.crop(crop_box)
                trim_box = None
                if trim:
                    cell_image, trim_box = trim_alpha(cell_image, trim_threshold)
                if padding:
                    cell_image = ImageOps.expand(cell_image, border=padding, fill=(0, 0, 0, 0))
                anchor_offset = (0, 0)
                if canvas_size:
                    cell_image, anchor_offset = place_on_canvas(cell_image, canvas_size, anchor)

                filename = f"{prefix}_{cell}.{output_format}"
                output_path = output_dir / filename
                save_image(cell_image, output_path, output_format)
                items.append(
                    {
                        "cell": cell,
                        "row": row,
                        "column": col,
                        "filename": filename,
                        "path": output_path.as_posix(),
                        "absolutePath": str(output_path.resolve()),
                        "cropBox": list(crop_box),
                        "trimBox": list(trim_box) if trim_box else None,
                        "anchor": anchor if canvas_size else None,
                        "anchorOffset": list(anchor_offset),
                        "width": cell_image.width,
                        "height": cell_image.height,
                        "sha256": sha256_file(output_path),
                    }
                )

    manifest = {
        "schemaVersion": 1,
        "tool": "slice-grid",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "source": {
            "path": input_path.as_posix(),
            "sha256": sha256_file(input_path),
        },
        "grid": {
            "rows": rows,
            "columns": cols,
            "outerMargin": asdict(margin),
            "gutter": asdict(gutter),
        },
        "processing": {
            "trimAlpha": trim,
            "trimThreshold": trim_threshold,
            "padding": padding,
            "canvas": list(canvas_size) if canvas_size else None,
            "anchor": anchor if canvas_size else None,
            "format": output_format,
        },
        "items": [{key: value for key, value in item.items() if key != "absolutePath"} for item in items],
    }

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if contact_sheet_path:
        make_contact_sheet(items, contact_sheet_path)

    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="拆分 2×2 / 3×3 / 4×4 RPG 资产板并生成追踪 Manifest")
    parser.add_argument("input", type=Path, help="PNG 或 WebP 资产板")
    parser.add_argument("output_dir", type=Path, help="切图输出目录")
    parser.add_argument("--rows", type=int, required=True, help="行数")
    parser.add_argument("--cols", type=int, required=True, help="列数")
    parser.add_argument("--outer-margin", type=parse_edges, default=Edges(), metavar="N|V,H|T,R,B,L")
    parser.add_argument("--gutter", type=parse_pair, default=Pair(), metavar="N|X,Y")
    parser.add_argument("--prefix", help="输出文件名前缀，默认使用输入文件名")
    parser.add_argument("--format", choices=("png", "webp"), default="png", dest="output_format")
    parser.add_argument("--trim-alpha", action="store_true", help="按透明通道裁除空白")
    parser.add_argument("--trim-threshold", type=int, default=4, help="透明裁剪阈值 0–255")
    parser.add_argument("--padding", type=int, default=0, help="透明裁剪后补回的像素边距")
    parser.add_argument("--canvas", type=parse_size, help="统一画布尺寸，例如 256x256")
    parser.add_argument("--anchor", choices=("center", "bottom-center", "top-left"), default="center")
    parser.add_argument("--manifest", type=Path, help="Manifest 输出路径")
    parser.add_argument("--contact-sheet", type=Path, help="联系表 PNG 输出路径")
    parser.add_argument("--overwrite", action="store_true", help="允许覆盖已有输出")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        manifest = slice_board(
            args.input,
            args.output_dir,
            rows=args.rows,
            cols=args.cols,
            margin=args.outer_margin,
            gutter=args.gutter,
            prefix=args.prefix,
            output_format=args.output_format,
            trim=args.trim_alpha,
            trim_threshold=args.trim_threshold,
            padding=args.padding,
            canvas_size=args.canvas,
            anchor=args.anchor,
            overwrite=args.overwrite,
            manifest_path=args.manifest,
            contact_sheet_path=args.contact_sheet,
        )
    except (SliceGridError, OSError) as exc:
        parser.error(str(exc))
    print(f"已输出 {len(manifest['items'])} 个素材：{args.output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
