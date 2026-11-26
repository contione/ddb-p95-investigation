#!/usr/bin/env python3
"""Print allowlisted package versions from a published .deps.json file."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable


EXACT_PACKAGE_NAMES = frozenset(
    {
        "awssdk.core",
        "awssdk.dynamodbv2",
        "awssdk.extensions.netcore.setup",
    }
)
PACKAGE_NAME_MARKERS = ("dynamo", "contione.ddb", "dce.ddb")
NUGET_PACKAGE_NAME = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?$")
NUGET_VERSION = re.compile(
    r"^[0-9]+(?:\.[0-9]+){0,3}"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)


def _is_allowlisted(package_name: str) -> bool:
    folded_name = package_name.casefold()
    return folded_name in EXACT_PACKAGE_NAMES or any(
        marker in folded_name for marker in PACKAGE_NAME_MARKERS
    )


def _split_package_key(value: Any) -> tuple[str, str] | None:
    if not isinstance(value, str):
        return None
    package_name, separator, version = value.rpartition("/")
    if not separator or not package_name or not version:
        return None
    if not NUGET_PACKAGE_NAME.fullmatch(package_name):
        return None
    if not NUGET_VERSION.fullmatch(version):
        return None
    return package_name, version


def _is_package_library(metadata: Any) -> bool:
    if not isinstance(metadata, dict):
        return True
    library_type = metadata.get("type")
    return library_type in (None, "package")


def _iter_target_keys(targets: Any) -> Iterable[str]:
    if not isinstance(targets, dict):
        return
    for target in targets.values():
        if not isinstance(target, dict):
            continue
        for key in target:
            if isinstance(key, str):
                yield key


def _collect_versions(document: dict[str, Any]) -> list[tuple[str, str]]:
    records: set[tuple[str, str]] = set()
    libraries = document.get("libraries")
    library_keys: dict[str, Any] = libraries if isinstance(libraries, dict) else {}

    for key, metadata in library_keys.items():
        if not _is_package_library(metadata):
            continue
        entry = _split_package_key(key)
        if entry is not None and _is_allowlisted(entry[0]):
            records.add(entry)

    for key in _iter_target_keys(document.get("targets")):
        entry = _split_package_key(key)
        if entry is None or not _is_allowlisted(entry[0]):
            continue
        if library_keys:
            if key not in library_keys or not _is_package_library(library_keys[key]):
                continue
        records.add(entry)

    return sorted(records, key=lambda item: (item[0].casefold(), item[1]))


def _usage(stream: Any) -> None:
    print("Usage: inspect_deps.py <published .deps.json>", file=stream)


def main(arguments: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if arguments is None else arguments

    if arguments == ["--help"] or arguments == ["-h"]:
        _usage(sys.stdout)
        return 0
    if len(arguments) != 1 or arguments[0].startswith("-"):
        print("Error: provide exactly one published .deps.json file.", file=sys.stderr)
        _usage(sys.stderr)
        return 2

    try:
        document = json.loads(Path(arguments[0]).read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        print("Error: unable to read a valid .deps.json file.", file=sys.stderr)
        return 1

    if not isinstance(document, dict) or not any(
        isinstance(document.get(field), dict) for field in ("libraries", "targets")
    ):
        print("Error: the input is not a valid .deps.json document.", file=sys.stderr)
        return 1

    for package_name, version in _collect_versions(document):
        print(f"{package_name} {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
