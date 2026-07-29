from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

MODULE_PATH = Path(__file__).resolve().parents[1] / "slice_grid.py"
SPEC = importlib.util.spec_from_file_location("slice_grid", MODULE_PATH)
assert SPEC and SPEC.loader
slice_grid = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = slice_grid
SPEC.loader.exec_module(slice_grid)


class SliceGridTests(unittest.TestCase):
    def make_board(self, path: Path) -> None:
        image = Image.new("RGBA", (220, 220), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        # 10px outer margin, 10px gutter, 95px cells.
        colors = [(255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255), (255, 255, 0, 255)]
        boxes = [(20, 20, 90, 90), (130, 20, 200, 90), (20, 130, 90, 200), (130, 130, 200, 200)]
        for box, color in zip(boxes, colors, strict=True):
            draw.rectangle(box, fill=color)
        image.save(path)

    def test_parse_helpers(self) -> None:
        self.assertEqual(slice_grid.parse_edges("8"), slice_grid.Edges(8, 8, 8, 8))
        self.assertEqual(slice_grid.parse_edges("4,8"), slice_grid.Edges(4, 8, 4, 8))
        self.assertEqual(slice_grid.parse_pair("6,10"), slice_grid.Pair(6, 10))
        self.assertEqual(slice_grid.parse_size("256x512"), (256, 512))
        self.assertEqual(slice_grid.row_label(0), "a")
        self.assertEqual(slice_grid.row_label(26), "aa")

    def test_split_trim_canvas_manifest_and_contact_sheet(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "board.png"
            output = root / "out"
            contact = root / "contact.png"
            self.make_board(source)

            manifest = slice_grid.slice_board(
                source,
                output,
                rows=2,
                cols=2,
                margin=slice_grid.Edges(10, 10, 10, 10),
                gutter=slice_grid.Pair(10, 10),
                prefix="env_test",
                trim=True,
                trim_threshold=1,
                padding=2,
                canvas_size=(96, 96),
                anchor="bottom-center",
                contact_sheet_path=contact,
            )

            self.assertEqual([item["cell"] for item in manifest["items"]], ["a1", "a2", "b1", "b2"])
            self.assertTrue(contact.is_file())
            self.assertEqual(len(list(output.glob("env_test_*.png"))), 4)
            with Image.open(output / "env_test_a1.png") as item:
                self.assertEqual(item.size, (96, 96))
                self.assertEqual(item.getpixel((48, 93))[:3], (255, 0, 0))

            stored = json.loads((output / "env_test.manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(stored["grid"]["rows"], 2)
            self.assertEqual(len(stored["items"]), 4)
            self.assertTrue(all(len(item["sha256"]) == 64 for item in stored["items"]))

    def test_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "board.png"
            output = root / "out"
            self.make_board(source)
            kwargs = dict(
                rows=2,
                cols=2,
                margin=slice_grid.Edges(10, 10, 10, 10),
                gutter=slice_grid.Pair(10, 10),
                prefix="asset",
            )
            slice_grid.slice_board(source, output, **kwargs)
            with self.assertRaises(slice_grid.SliceGridError):
                slice_grid.slice_board(source, output, **kwargs)


if __name__ == "__main__":
    unittest.main()
