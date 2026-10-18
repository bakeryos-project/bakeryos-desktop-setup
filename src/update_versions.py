#!/usr/bin/env python3

import argparse
import json
import os
import sys
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
EXTENSIONS_JSON = SCRIPT_DIR / "extensions.json"
DEFAULT_SHELL_VERSION = 51


class FetchExtensionMetadataFailed(Exception):
    pass


def load_extensions():
    try:
        with open(EXTENSIONS_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {EXTENSIONS_JSON} not found.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse {EXTENSIONS_JSON}: {e}")
        sys.exit(1)


def save_extensions(data):
    with open(EXTENSIONS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def get_latest_compatible_version(extension_id: str, target_shell_version: int):
    """Return the newest version string that supports target_shell_version."""
    page = 1
    page_size = 50
    all_results = []

    while True:
        url = (
            "https://extensions.gnome.org/api/v1/extensions/"
            f"{extension_id}/versions/?page_size={page_size}&page={page}"
        )
        try:
            resp = requests.get(url, timeout=30)
        except requests.RequestException as e:
            raise FetchExtensionMetadataFailed(
                f"Request error for {extension_id}: {e}"
            )

        if not resp.ok:
            raise FetchExtensionMetadataFailed(
                f"HTTP {resp.status_code} for {extension_id}"
            )

        data = resp.json()
        results = data.get("results", [])
        if not results:
            break

        all_results.extend(results)

        if not data.get("next"):
            break
        page += 1

    if not all_results:
        raise FetchExtensionMetadataFailed(f"No versions found for {extension_id}")

    # Keep only versions whose shell_versions list contains the target major.
    compatible = []
    for v in all_results:
        shell_versions = v.get("shell_versions", [])
        for sv in shell_versions:
            if sv.get("major") == target_shell_version:
                compatible.append(v)
                break

    if not compatible:
        raise FetchExtensionMetadataFailed(
            f"No version supporting GNOME Shell {target_shell_version} for {extension_id}"
        )

    def sort_key(v):
        try:
            ver = int(v.get("version", 0))
        except (ValueError, TypeError):
            ver = 0
        created = v.get("created", "") or ""
        return (ver, created)

    latest = max(compatible, key=sort_key)
    return latest.get("version")


def main():
    parser = argparse.ArgumentParser(
        description="Check and update GNOME extension versions in extensions.json."
    )
    parser.add_argument(
        "--shell-version",
        type=int,
        default=DEFAULT_SHELL_VERSION,
        help="Target GNOME Shell major version (default: 51).",
    )
    args = parser.parse_args()
    shell_version = args.shell_version

    print(f"Target GNOME Shell major version: {shell_version}")
    print(f"Reading {EXTENSIONS_JSON} ...")

    extensions = load_extensions()
    changed = False
    updated = []

    for entry in extensions:
        ext_id = entry.get("name")
        if not ext_id:
            continue
        pinned = entry.get("version", "")

        try:
            latest = get_latest_compatible_version(ext_id, shell_version)
        except Exception as e:
            print(f"  [SKIP]  {ext_id}: {e}")
            continue

        latest_str = str(latest)
        need_update = False
        reason = ""

        if not pinned:
            need_update = True
            reason = f"no pinned version, setting to {latest_str}"
        else:
            try:
                if int(pinned) < int(latest_str):
                    need_update = True
                    reason = f"{pinned} -> {latest_str}"
                else:
                    print(f"  [OK]    {ext_id}: {pinned} (latest {latest_str})")
            except ValueError:
                need_update = True
                reason = f"invalid pinned '{pinned}', updating to {latest_str}"

        if need_update:
            print(f"  [UPDATE] {ext_id}: {reason}")
            entry["version"] = latest_str
            changed = True
            updated.append({"name": ext_id, "version": latest_str})

    if changed:
        save_extensions(extensions)
        print(f"\nUpdated {len(updated)} extension(s) in {EXTENSIONS_JSON}.")
        gh_output = os.getenv("GITHUB_OUTPUT")
        if gh_output:
            with open(gh_output, "a", encoding="utf-8") as f:
                f.write("changed=true\n")
    else:
        print("\nNo extensions need updating.")
        gh_output = os.getenv("GITHUB_OUTPUT")
        if gh_output:
            with open(gh_output, "a", encoding="utf-8") as f:
                f.write("changed=false\n")


if __name__ == "__main__":
    main()
