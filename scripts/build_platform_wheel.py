#!/usr/bin/env python3
"""Build platform-specific wheels by injecting upstream fnox binaries.

Usage:
    python scripts/build_platform_wheel.py --fnox-version 1.0.0 --output dist/

Workflow:
    1. Build a pure wheel with `uv build --wheel`
    2. For each platform, download the upstream fnox binary from GitHub releases
    3. Unpack the pure wheel, inject the binary into .data/scripts/
    4. Rewrite WHEEL metadata (platform tag, Root-Is-Purelib: false)
    5. Update RECORD, repack as a platform-specific wheel
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import shutil
import stat
import subprocess
import tarfile
import tempfile
import zipfile
from pathlib import Path

import urllib3
from rich.traceback import install

install()

PLATFORM_MAP: dict[str, str] = {
    "fnox-aarch64-apple-darwin": "macosx_11_0_arm64",
    "fnox-x86_64-apple-darwin": "macosx_10_12_x86_64",
    "fnox-aarch64-unknown-linux-gnu": "manylinux_2_17_aarch64",
    "fnox-x86_64-unknown-linux-gnu": "manylinux_2_17_x86_64",
    "fnox-aarch64-pc-windows-msvc": "win_arm64",
    "fnox-x86_64-pc-windows-msvc": "win_amd64",
}

GITHUB_RELEASE_URL = "https://github.com/jdx/fnox/releases/download"
GITHUB_LATEST_RELEASE_API_URL = "https://api.github.com/repos/jdx/fnox/releases/latest"


def _normalize_fnox_version(fnox_version: str) -> str:
    return fnox_version.removeprefix("v")


def _fetch_latest_release_tag() -> str:
    http = urllib3.PoolManager()
    try:
        response = http.request(
            "GET",
            GITHUB_LATEST_RELEASE_API_URL,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "fnox-py-release-helper",
            },
        )
    except urllib3.exceptions.HTTPError as exc:
        msg = f"Failed to fetch latest fnox release metadata: {exc}"
        raise RuntimeError(msg) from exc
    finally:
        http.clear()

    if response.status != 200:
        msg = f"Failed to fetch latest fnox release metadata: HTTP {response.status}"
        raise RuntimeError(msg)

    try:
        payload = json.loads(response.data)
    except json.JSONDecodeError as exc:
        msg = "GitHub latest release response was not valid JSON"
        raise RuntimeError(msg) from exc

    tag_name = payload.get("tag_name")
    if not isinstance(tag_name, str) or not tag_name:
        msg = "GitHub latest release response did not include a valid tag_name"
        raise RuntimeError(msg)
    return tag_name


def _resolve_fnox_version(requested_version: str | None) -> str:
    if requested_version:
        return _normalize_fnox_version(requested_version)
    return _normalize_fnox_version(_fetch_latest_release_tag())


def _download_binary(fnox_version: str, asset_name: str, dest: Path) -> Path:
    """Download an upstream fnox binary from GitHub releases."""
    is_windows = "windows" in asset_name
    ext = ".zip" if is_windows else ".tar.gz"
    url = f"{GITHUB_RELEASE_URL}/v{fnox_version}/{asset_name}{ext}"

    archive_path = dest / f"{asset_name}{ext}"

    subprocess.run(
        ["curl", "-fsSL", "-o", str(archive_path), url],
        check=True,
    )

    binary_name = "fnox.exe" if is_windows else "fnox"

    if is_windows:
        with zipfile.ZipFile(archive_path) as zf:
            for name in zf.namelist():
                if name.endswith(binary_name):
                    extracted = dest / binary_name
                    with zf.open(name) as src, extracted.open("wb") as dst:
                        dst.write(src.read())
                    return extracted
    else:
        with tarfile.open(archive_path) as tf:
            for member in tf.getmembers():
                if member.name.endswith(binary_name):
                    f = tf.extractfile(member)
                    if f is None:
                        continue
                    extracted = dest / binary_name
                    extracted.write_bytes(f.read())
                    extracted.chmod(extracted.stat().st_mode | stat.S_IEXEC)
                    return extracted

    msg = f"Could not find {binary_name} in archive {archive_path}"
    raise FileNotFoundError(msg)


def _file_sha256(path: Path) -> hashlib._Hash:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h


def _sha256_digest(path: Path) -> str:
    return _file_sha256(path).hexdigest()


def _record_hash(path: Path) -> str:
    """Compute hash in RECORD format: sha256=<urlsafe-base64>."""
    digest = base64.urlsafe_b64encode(_file_sha256(path).digest()).rstrip(b"=").decode()
    return f"sha256={digest}"


def _build_pure_wheel(output_dir: Path) -> Path:
    """Build a pure wheel using uv and return the wheel path."""
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(output_dir)],
        check=True,
    )
    wheels = list(output_dir.glob("*.whl"))
    if len(wheels) != 1:
        msg = f"Expected exactly one wheel, found {len(wheels)}: {wheels}"
        raise RuntimeError(msg)
    return wheels[0]


def _inject_binary(work: Path, name_version: str, binary_path: Path, platform_tag: str) -> None:
    """Place the binary into .data/scripts/ and set permissions."""
    data_dir = work / f"{name_version}.data"
    scripts_dir = data_dir / "scripts"
    scripts_dir.mkdir(parents=True)

    is_windows = "win" in platform_tag
    binary_dest_name = "fnox.exe" if is_windows else "fnox"
    dest_binary = scripts_dir / binary_dest_name
    shutil.copy2(binary_path, dest_binary)
    if not is_windows:
        dest_binary.chmod(dest_binary.stat().st_mode | stat.S_IEXEC)


def _rewrite_wheel_metadata(dist_info: Path, platform_tag: str) -> None:
    """Rewrite WHEEL file with platform tag and Root-Is-Purelib: false."""
    wheel_file = dist_info / "WHEEL"
    new_lines = []
    has_root_is_purelib = False
    for line in wheel_file.read_text().splitlines():
        if line.startswith("Tag:"):
            new_lines.append(f"Tag: py3-none-{platform_tag}")
        elif line.startswith("Root-Is-Purelib:"):
            new_lines.append("Root-Is-Purelib: false")
            has_root_is_purelib = True
        else:
            new_lines.append(line)
    if not has_root_is_purelib:
        new_lines.append("Root-Is-Purelib: false")
    wheel_file.write_text("\n".join(new_lines) + "\n")


def _rebuild_record(work: Path, dist_info: Path) -> None:
    """Regenerate the RECORD file with hashes for all files."""
    record_file = dist_info / "RECORD"
    record_rel = record_file.relative_to(work)
    entries: list[str] = []
    for file_path in sorted(work.rglob("*")):
        if file_path.is_dir():
            continue
        rel = file_path.relative_to(work)
        if rel == record_rel:
            continue
        entries.append(f"{rel},{_record_hash(file_path)},{file_path.stat().st_size}")
    entries.append(f"{record_rel},,")
    record_file.write_text("\n".join(entries) + "\n")


def _repack_wheel(
    pure_wheel: Path,
    binary_path: Path,
    platform_tag: str,
    output_dir: Path,
) -> Path:
    """Inject binary and rewrite metadata to create a platform-specific wheel."""
    with tempfile.TemporaryDirectory() as tmpdir:
        work = Path(tmpdir) / "wheel"

        with zipfile.ZipFile(pure_wheel) as zf:
            zf.extractall(work)
        dist_infos = list(work.glob("*.dist-info"))
        if len(dist_infos) != 1:
            msg = f"Expected one dist-info, found {len(dist_infos)}"
            raise RuntimeError(msg)
        dist_info = dist_infos[0]
        name_version = dist_info.name.removesuffix(".dist-info")

        _inject_binary(work, name_version, binary_path, platform_tag)
        _rewrite_wheel_metadata(dist_info, platform_tag)
        _rebuild_record(work, dist_info)

        out_name = f"{name_version}-py3-none-{platform_tag}.whl"
        out_path = output_dir / out_name

        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in sorted(work.rglob("*")):
                if file_path.is_dir():
                    continue
                zf.write(file_path, file_path.relative_to(work))

        return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build platform-specific fnox-py wheels")
    parser.add_argument(
        "--fnox-version",
        help="Upstream fnox version (e.g. 1.0.0). Defaults to the latest upstream release.",
    )
    parser.add_argument("--output", default="dist", help="Output directory for wheels")
    parser.add_argument(
        "--platforms",
        nargs="*",
        default=list(PLATFORM_MAP.keys()),
        choices=list(PLATFORM_MAP.keys()),
        help="Platforms to build (default: all)",
    )
    args = parser.parse_args()
    fnox_version = _resolve_fnox_version(args.fnox_version)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Using upstream fnox version: {fnox_version}")

    with tempfile.TemporaryDirectory() as pure_dir:
        pure_wheel = _build_pure_wheel(Path(pure_dir))
        print(f"Built pure wheel: {pure_wheel.name}")

        for asset_name in args.platforms:
            platform_tag = PLATFORM_MAP[asset_name]
            print(f"\nBuilding {platform_tag}...")

            with tempfile.TemporaryDirectory() as dl_dir:
                binary = _download_binary(fnox_version, asset_name, Path(dl_dir))
                print(f"  Downloaded: {binary.name} ({binary.stat().st_size} bytes)")
                print(f"  SHA256: {_sha256_digest(binary)}")

                out = _repack_wheel(pure_wheel, binary, platform_tag, output_dir)
                print(f"  Created: {out.name}")

    print("\nBuilding sdist...")
    subprocess.run(
        ["uv", "build", "--sdist", "--out-dir", str(output_dir)],
        check=True,
    )

    print("\nDone! Artifacts:")
    for artifact in sorted(output_dir.glob("*")):
        print(f"  {artifact.name}")


if __name__ == "__main__":
    main()
