#!/usr/bin/env python3
"""Validate the Shuangjin asset manifest and referenced repository files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


class ValidationError(Exception):
    """Raised when the asset manifest is inconsistent."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationError(f"Manifest not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(
            f"Invalid JSON in {path}: line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc

    if not isinstance(data, dict):
        raise ValidationError("Manifest root must be a JSON object")
    return data


def require_non_empty_string(value: Any, field: str, asset_id: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{asset_id}: {field} must be a non-empty string")
    return value


def validate_repo_path(repo_root: Path, raw_path: Any, field: str, asset_id: str) -> None:
    path_text = require_non_empty_string(raw_path, field, asset_id)
    path = Path(path_text)
    if path.is_absolute() or ".." in path.parts:
        raise ValidationError(f"{asset_id}: {field} must be a safe repository-relative path")
    target = repo_root / path
    if not target.exists():
        raise ValidationError(f"{asset_id}: {field} does not exist: {path_text}")


def validate_manifest(manifest: dict[str, Any], repo_root: Path) -> list[str]:
    errors: list[str] = []

    def record(callable_) -> None:
        try:
            callable_()
        except ValidationError as exc:
            errors.append(str(exc))

    status_flow = manifest.get("statusFlow")
    if not isinstance(status_flow, list) or not status_flow:
        errors.append("statusFlow must be a non-empty array")
        allowed_statuses: set[str] = set()
    elif not all(isinstance(item, str) and item for item in status_flow):
        errors.append("statusFlow may only contain non-empty strings")
        allowed_statuses = set()
    else:
        allowed_statuses = set(status_flow)
        if len(allowed_statuses) != len(status_flow):
            errors.append("statusFlow contains duplicate states")

    assets = manifest.get("assets")
    if not isinstance(assets, list):
        return errors + ["assets must be an array"]

    seen_ids: set[str] = set()
    for index, asset in enumerate(assets):
        if not isinstance(asset, dict):
            errors.append(f"assets[{index}] must be an object")
            continue

        asset_id = asset.get("id")
        if not isinstance(asset_id, str) or not asset_id.strip():
            errors.append(f"assets[{index}].id must be a non-empty string")
            asset_id = f"assets[{index}]"
        elif asset_id in seen_ids:
            errors.append(f"duplicate asset id: {asset_id}")
        else:
            seen_ids.add(asset_id)

        for field in ("name", "category", "chapter", "batch"):
            record(lambda f=field, a=asset_id: require_non_empty_string(asset.get(f), f, a))

        status = asset.get("status")
        if status not in allowed_statuses:
            errors.append(f"{asset_id}: invalid status {status!r}")

        prompt_file = asset.get("promptFile")
        if prompt_file is not None:
            record(
                lambda p=prompt_file, a=asset_id: validate_repo_path(
                    repo_root, p, "promptFile", a
                )
            )
        elif status not in {"BACKLOG", "DONE"} and asset.get("category") != "tooling":
            errors.append(f"{asset_id}: active non-tooling asset must declare promptFile")

        source_file = asset.get("sourceFile")
        if source_file is not None:
            record(
                lambda p=source_file, a=asset_id: validate_repo_path(
                    repo_root, p, "sourceFile", a
                )
            )

        runtime_files = asset.get("runtimeFiles", [])
        if not isinstance(runtime_files, list):
            errors.append(f"{asset_id}: runtimeFiles must be an array")
            runtime_files = []
        for file_index, runtime_file in enumerate(runtime_files):
            record(
                lambda p=runtime_file, a=asset_id, i=file_index: validate_repo_path(
                    repo_root, p, f"runtimeFiles[{i}]", a
                )
            )

        if status == "DONE" and source_file is None and not runtime_files:
            errors.append(f"{asset_id}: DONE asset must declare sourceFile or runtimeFiles")

        issue = asset.get("issue")
        if issue is not None and (not isinstance(issue, int) or issue <= 0):
            errors.append(f"{asset_id}: issue must be a positive integer")

        attempts = asset.get("generationAttempts", [])
        if attempts is not None and not isinstance(attempts, list):
            errors.append(f"{asset_id}: generationAttempts must be an array")

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Repository root; defaults to two levels above this script",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("manifests/assets-manifest.json"),
        help="Manifest path relative to repo root",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    manifest_path = args.manifest
    if not manifest_path.is_absolute():
        manifest_path = repo_root / manifest_path

    try:
        manifest = load_json(manifest_path)
    except ValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    errors = validate_manifest(manifest, repo_root)
    if errors:
        print(f"Asset manifest validation failed with {len(errors)} error(s):", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    assets = manifest.get("assets", [])
    print(f"Asset manifest valid: {len(assets)} assets checked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
