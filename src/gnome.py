import argparse
import json
import os
import subprocess
import zipfile
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
EXTENSIONS_JSON = SCRIPT_DIR / "extensions.json"


class FetchExtensionMetadataFailed(Exception):
    pass


def load_extensions() -> list:
    """Load extension list and pinned versions from extensions.json."""
    try:
        with open(EXTENSIONS_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Warning: {EXTENSIONS_JSON} not found, using empty extension list.")
        return []
    except json.JSONDecodeError as e:
        print(f"Warning: Failed to parse {EXTENSIONS_JSON}: {e}")
        return []

    extensions = []
    for entry in data:
        name = entry.get("name")
        if not name:
            continue
        extensions.append(
            {
                "name": name,
                "version": entry.get("version", ""),
            }
        )
    return extensions


def get_local_shell_version() -> int:
    try:
        result = subprocess.run(["gnome-shell", "--version"], capture_output=True, text=True, check=True)
        output = result.stdout.strip()
        for part in output.split():
            if "." in part or part.isdigit():
                return int(part.split(".")[0])
    except Exception as e:
        print("Failed to detect local shell version", e)
    return 46


def get_latest_version(extension_id: str, target_shell_version: int) -> int:
    page = 1
    page_size = 50
    all_results = []

    while True:
        api_url = f"https://extensions.gnome.org/api/v1/extensions/{extension_id}/versions/?page_size={page_size}&page={page}"
        response = requests.get(api_url)

        if not response.ok:
            raise FetchExtensionMetadataFailed(f"HTTP error {response.status_code}: Failed to fetch metadata for {extension_id}")

        data = response.json()
        results = data.get("results", [])
        if not results:
            break

        all_results.extend(results)

        if not data.get("next"):
            break
        page += 1

    if not all_results:
        raise FetchExtensionMetadataFailed("No version found for this extension.")

    compatible_versions = []
    for v in all_results:
        shell_versions = v.get("shell_versions", [])
        for sv in shell_versions:
            if sv.get("major") == target_shell_version:
                compatible_versions.append(v)
                break

    if not compatible_versions:
        raise FetchExtensionMetadataFailed(f"No version found supporting GNOME Shell {target_shell_version}")

    latest = max(compatible_versions, key=lambda x: (x.get("version", 0), x.get("created", "")))
    return latest["version"]


def download_extension(extension_id: str, version: int, download_dir: Path) -> Path:
    clean_id = extension_id.replace('@', '')
    full_url = f"https://extensions.gnome.org/extension-data/{clean_id}.v{version}.shell-extension.zip"
    target_zip = download_dir / f"{extension_id}.zip"

    print(f"Loading extension: {extension_id} (Version: {version})")
    response = requests.get(full_url)
    response.raise_for_status()

    target_zip.write_bytes(response.content)
    return target_zip


def extract_and_chmod(target_zip: Path, extract_dir: Path, extension_id: str):
    print(f"Extracting extensions: {extension_id}")
    target_ext_dir = extract_dir / extension_id
    target_ext_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(target_zip, 'r') as zip_ref:
        zip_ref.extractall(target_ext_dir)

    if os.name == 'posix':
        for path in target_ext_dir.rglob('*'):
            if path.is_file() and path.suffix in ('.js', '.sh'):
                try:
                    current_mode = path.stat().st_mode
                    path.chmod(current_mode | 0o111)
                except Exception as e:
                    print(f"Warning: Failed to chmod {path}: {e}")

    schemas_dir = target_ext_dir / "schemas"
    if schemas_dir.exists() and schemas_dir.is_dir():
        print(f"Compiling gschema for {extension_id}...")
        try:
            result = subprocess.run(["glib-compile-schemas", str(schemas_dir)], capture_output=True, text=True, check=True)
            if result.returncode == 0:
                print("Successfully compiled gschema!")
            else:
                print(f"Warning: glib-compile-schemas exited with error: {result.stderr.strip()}")
        except FileNotFoundError:
            print("Unable to run glib-compile-schemas (glib2 might not be installed).")


def main():
    parser = argparse.ArgumentParser(description="Download and install GNOME Shell extensions.")
    parser.add_argument("dest_dir", type=Path, help="Destination directory")
    parser.add_argument("--shell-version", type=int, help="Target GNOME Shell major version (e.g., 46, 47, 48). Auto-detected if not specified.")
    args = parser.parse_args()

    shell_version = args.shell_version
    if shell_version is None:
        shell_version = get_local_shell_version()
        print(f"Auto-detected GNOME Shell major version: {shell_version}")
    else:
        print(f"Using specified GNOME Shell major version: {shell_version}")

    dest_dir = Path(args.dest_dir)
    download_dir = dest_dir / "downloads"
    extract_dir = dest_dir / "extract"

    download_dir.mkdir(parents=True, exist_ok=True)
    extract_dir.mkdir(parents=True, exist_ok=True)

    extensions = load_extensions()

    for ext in extensions:
        extension_id = ext["name"]
        pinned_version = ext["version"]

        try:
            latest_version = get_latest_version(extension_id, shell_version)
        except Exception as e:
            print(f"Error: {e}")
            print(f"Skipping: No version found for {extension_id}")
            continue

        print(
            f"Extension: {extension_id} | pinned version: {pinned_version or '-'} | "
            f"latest compatible: {latest_version}"
        )

        try:
            target_zip = download_extension(extension_id, latest_version, download_dir)
        except Exception as e:
            print(f"Error downloading {extension_id}: {e}")
            continue

        try:
            extract_and_chmod(target_zip, extract_dir, extension_id)
        except Exception as e:
            print(f"Error extracting {extension_id}: {e}")

    print("\nPackaging extensions completed successfully into:", extract_dir)


if __name__ == "__main__":
    main()
