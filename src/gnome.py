import math
import os
import subprocess
import zipfile
import argparse
from pathlib import Path

import requests

GNOME_EXTENSIONS = [
    "dash-to-panel@jderose9.github.com",
    "blur-my-shell@aunetx",
    "tilingshell@ferrarodomenico.com",
    "arcmenu@arcmenu.com",
    "gtk4-ding@smedius.gitlab.com",
    "clipboard-history@alexsaveau.dev",
    "Vitals@CoreCoding.com",
]

class FetchExtensionMetadataFailed(Exception):
    pass

def get_latest_version(extension_id: str) -> int:
    page_size = 20
    api_url = f"https://extensions.gnome.org/api/v1/extensions/{extension_id}/versions/?page_size={page_size}"
    response = requests.get(api_url)

    if not response.ok:
        raise FetchExtensionMetadataFailed(f"HTTP error {response.status_code}: Failed to fetch metadata for {extension_id}")

    data = response.json()
    count = data.get("count", 0)
    if count == 0:
        raise FetchExtensionMetadataFailed("No version found for this extension (count = 0)")

    total_pages = math.ceil(count / page_size)

    if total_pages > 1:
        last_page_url = f"https://extensions.gnome.org/api/v1/extensions/{extension_id}/versions/?page_size={page_size}&page={total_pages}"
        resp = requests.get(last_page_url)
        if not resp.ok:
            raise FetchExtensionMetadataFailed(f"HTTP error {resp.status_code}: Failed to fetch last page")
        data = resp.json()

    results = data.get("results", [])
    if not results:
        raise FetchExtensionMetadataFailed("The returned result list is empty even though count > 0.")

    return results[-1]["version"]

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
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("dest_dir", type=Path, help="")
    args = parser.parse_args()

    dest_dir = Path(args.dest_dir)
    download_dir = dest_dir / "downloads"
    extract_dir = dest_dir / "extract"

    download_dir.mkdir(parents=True, exist_ok=True)
    extract_dir.mkdir(parents=True, exist_ok=True)

    for extension_id in GNOME_EXTENSIONS:
        try:
            version = get_latest_version(extension_id)
            print(f"Detected the latest version: {version}")
        except Exception as e:
            print(f"Error: {e}")
            print(f"Skipping: No version found for {extension_id}")
            continue

        try:
            target_zip = download_extension(extension_id, version, download_dir)
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
