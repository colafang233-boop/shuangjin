from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "validate_manifest.py"
SPEC = importlib.util.spec_from_file_location("validate_manifest", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ValidateManifestTests(unittest.TestCase):
    def make_repo(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / "prompts").mkdir()
        (root / "tools").mkdir()
        (root / "prompts" / "asset.md").write_text("prompt", encoding="utf-8")
        (root / "tools" / "tool.py").write_text("print('ok')", encoding="utf-8")
        return temp, root

    def valid_manifest(self) -> dict:
        return {
            "schemaVersion": 1,
            "statusFlow": ["BACKLOG", "GENERATING", "DONE", "REJECTED"],
            "assets": [
                {
                    "id": "character-001",
                    "name": "Character",
                    "category": "character",
                    "chapter": "chapter-01",
                    "batch": "S00-01",
                    "status": "GENERATING",
                    "sourceFile": None,
                    "promptFile": "prompts/asset.md",
                    "runtimeFiles": [],
                    "issue": 2,
                },
                {
                    "id": "tool-001",
                    "name": "Tool",
                    "category": "tooling",
                    "chapter": "global",
                    "batch": "PIPELINE-01",
                    "status": "DONE",
                    "sourceFile": "tools/tool.py",
                    "promptFile": None,
                    "runtimeFiles": [],
                },
            ],
        }

    def test_valid_manifest_passes(self) -> None:
        temp, root = self.make_repo()
        self.addCleanup(temp.cleanup)
        errors = MODULE.validate_manifest(self.valid_manifest(), root)
        self.assertEqual(errors, [])

    def test_duplicate_id_and_missing_file_fail(self) -> None:
        temp, root = self.make_repo()
        self.addCleanup(temp.cleanup)
        manifest = self.valid_manifest()
        duplicate = dict(manifest["assets"][0])
        duplicate["promptFile"] = "prompts/missing.md"
        manifest["assets"].append(duplicate)
        errors = MODULE.validate_manifest(manifest, root)
        self.assertTrue(any("duplicate asset id" in error for error in errors))
        self.assertTrue(any("does not exist" in error for error in errors))

    def test_done_asset_requires_delivery_path(self) -> None:
        temp, root = self.make_repo()
        self.addCleanup(temp.cleanup)
        manifest = self.valid_manifest()
        manifest["assets"] = [
            {
                "id": "empty-done",
                "name": "Empty",
                "category": "tooling",
                "chapter": "global",
                "batch": "T-01",
                "status": "DONE",
                "sourceFile": None,
                "promptFile": None,
                "runtimeFiles": [],
            }
        ]
        errors = MODULE.validate_manifest(manifest, root)
        self.assertTrue(any("DONE asset" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
