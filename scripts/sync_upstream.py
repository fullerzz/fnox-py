#!/usr/bin/env python3
"""Fetch the latest jdx/fnox release and update FNOX_VERSION.txt + FNOX_HASHES.json.

Usage:
    python scripts/sync_upstream.py [--token TOKEN] [--dry-run] [--force]

Structured stdout for workflow consumption:
    VERSION=1.19.0
    RELEASE_URL=https://github.com/jdx/fnox/releases/tag/v1.19.0
    UPDATED=true
    RELEASE_NOTES_START
    <upstream release notes markdown>
    RELEASE_NOTES_END
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import TypedDict
from urllib.request import Request, urlopen

from rich.traceback import install

install()

REPO_ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = REPO_ROOT / "FNOX_VERSION.txt"
HASHES_FILE = REPO_ROOT / "FNOX_HASHES.json"

GITHUB_API_URL = "https://api.github.com/repos/jdx/fnox/releases/latest"
GITHUB_RELEASE_URL = "https://github.com/jdx/fnox/releases/download"

ASSET_NAMES: list[str] = [
    "fnox-aarch64-apple-darwin",
    "fnox-aarch64-pc-windows-msvc",
    "fnox-aarch64-unknown-linux-gnu",
    "fnox-x86_64-apple-darwin",
    "fnox-x86_64-pc-windows-msvc",
    "fnox-x86_64-unknown-linux-gnu",
]


class ReleaseInfo(TypedDict):
    tag_name: str
    html_url: str
    body: str


class AssetHashes(TypedDict):
    archive_sha256: str
    binary_sha256: str


def _fetch_latest_release(token: str | None = None) -> ReleaseInfo:
    """GET /repos/jdx/fnox/releases/latest and return release metadata."""
    req = Request(GITHUB_API_URL)  # noqa: S310
    req.add_header("Accept", "application/vnd.github+json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    with urlopen(req) as resp:  # noqa: S310
        data = json.loads(resp.read().decode())

    return ReleaseInfo(
        tag_name=data["tag_name"],
        html_url=data["html_url"],
        body=data.get("body", ""),
    )


def _normalize_version(tag: str) -> str:
    return tag.removeprefix("v")


def _read_current_version() -> str | None:
    if not VERSION_FILE.is_file():
        return None
    text = VERSION_FILE.read_text().strip()
    return text if text else None


def _archive_url(version: str, asset_name: str) -> str:
    ext = ".zip" if "windows" in asset_name else ".tar.gz"
    return f"{GITHUB_RELEASE_URL}/v{version}/{asset_name}{ext}"


def _download_archive(url: str, dest: Path) -> None:
    subprocess.run(["curl", "-fsSL", "-o", str(dest), url], check=True)


def _sha256_digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _extract_binary_and_hash(archive: Path, asset_name: str, work_dir: Path) -> str:
    """Open tar/zip archive, find fnox binary, extract it, and return its SHA256."""
    is_windows = "windows" in asset_name
    binary_name = "fnox.exe" if is_windows else "fnox"

    if is_windows:
        with zipfile.ZipFile(archive) as zf:
            for name in zf.namelist():
                if name.endswith(binary_name):
                    extracted = work_dir / binary_name
                    with zf.open(name) as src, extracted.open("wb") as dst:
                        dst.write(src.read())
                    return _sha256_digest(extracted)
    else:
        with tarfile.open(archive) as tf:
            for member in tf.getmembers():
                if member.name.endswith(binary_name):
                    f = tf.extractfile(member)
                    if f is None:
                        continue
                    extracted = work_dir / binary_name
                    extracted.write_bytes(f.read())
                    return _sha256_digest(extracted)

    msg = f"Could not find {binary_name} in archive {archive.name}"
    raise FileNotFoundError(msg)


def _compute_platform_hashes(version: str, work_dir: Path) -> dict[str, AssetHashes]:
    """Download and hash all platform archives and binaries."""
    hashes: dict[str, AssetHashes] = {}

    for asset_name in ASSET_NAMES:
        url = _archive_url(version, asset_name)
        ext = ".zip" if "windows" in asset_name else ".tar.gz"
        archive_path = work_dir / f"{asset_name}{ext}"

        print(f"  Downloading {asset_name}...")
        _download_archive(url, archive_path)
        archive_hash = _sha256_digest(archive_path)

        binary_dir = work_dir / asset_name
        binary_dir.mkdir()
        binary_hash = _extract_binary_and_hash(archive_path, asset_name, binary_dir)

        hashes[asset_name] = AssetHashes(
            archive_sha256=archive_hash,
            binary_sha256=binary_hash,
        )
        print(f"    archive: {archive_hash}")
        print(f"    binary:  {binary_hash}")

    return hashes


def _write_version_file(version: str) -> None:
    VERSION_FILE.write_text(version + "\n")


def _write_hashes_file(version: str, hashes: dict[str, AssetHashes]) -> None:
    data = {version: hashes}
    HASHES_FILE.write_text(json.dumps(data, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync fnox-py with latest upstream jdx/fnox release")
    parser.add_argument("--token", help="GitHub API token (or set GH_TOKEN / GITHUB_TOKEN env var)")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and compute but do not write files")
    parser.add_argument("--force", action="store_true", help="Update even if version matches")
    args = parser.parse_args()

    token = args.token or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

    print("Fetching latest jdx/fnox release...")
    release = _fetch_latest_release(token)
    latest_version = _normalize_version(release["tag_name"])
    current_version = _read_current_version()

    print(f"  Current: {current_version}")
    print(f"  Latest:  {latest_version}")

    if current_version == latest_version and not args.force:
        print("Already up to date.")
        print(f"VERSION={latest_version}")
        print(f"RELEASE_URL={release['html_url']}")
        print("UPDATED=false")
        return

    print(f"\nComputing hashes for v{latest_version}...")
    with tempfile.TemporaryDirectory() as work_dir:
        hashes = _compute_platform_hashes(latest_version, Path(work_dir))

    if not args.dry_run:
        _write_version_file(latest_version)
        _write_hashes_file(latest_version, hashes)
        print(f"\nUpdated FNOX_VERSION.txt and FNOX_HASHES.json to {latest_version}")
    else:
        print("\nDry run — files not written.")

    print(f"VERSION={latest_version}")
    print(f"RELEASE_URL={release['html_url']}")
    print("UPDATED=true")
    print("RELEASE_NOTES_START")
    print(release["body"])
    print("RELEASE_NOTES_END")


if __name__ == "__main__":
    main()
