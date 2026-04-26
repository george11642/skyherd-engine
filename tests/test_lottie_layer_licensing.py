"""Phase E2 license-sweep gate for Lottie primitives.

Mirrors the Phase D B-roll license test: every ``.json`` in
``remotion-video/public/lottie/`` MUST be listed in ``SOURCE.md`` with
either a CC0 or MIT license, and no GPL/AGPL/LGPL/proprietary/royalty
tokens may declare a license for an asset.
"""

from __future__ import annotations

import hashlib
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
LOTTIE_DIR = ROOT / "remotion-video" / "public" / "lottie"
SOURCE_MD = LOTTIE_DIR / "SOURCE.md"

ALLOWED_LICENSES: frozenset[str] = frozenset({"CC0", "MIT"})

FORBIDDEN_LICENSE_TOKENS: tuple[str, ...] = (
    "AGPL",
    "GPL",
    "LGPL",
    "proprietary",
    "royalty",
)


@pytest.fixture(scope="module")
def source_md_text() -> str:
    assert SOURCE_MD.exists(), f"SOURCE.md missing at {SOURCE_MD}"
    return SOURCE_MD.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def lottie_filenames() -> list[str]:
    return sorted(p.name for p in LOTTIE_DIR.glob("*.json"))


def test_lottie_directory_exists() -> None:
    assert LOTTIE_DIR.is_dir(), f"{LOTTIE_DIR} does not exist"


def test_source_md_exists() -> None:
    assert SOURCE_MD.is_file(), f"{SOURCE_MD} does not exist"


def test_at_least_three_primitives_present(lottie_filenames: list[str]) -> None:
    """Phase E2 plan: 3-5 Lottie animations. We ship 5."""
    assert len(lottie_filenames) >= 3, (
        f"Phase E2 needs ≥3 Lottie animations; found {lottie_filenames}"
    )


def test_every_lottie_listed_in_source_md(lottie_filenames: list[str], source_md_text: str) -> None:
    missing = [f for f in lottie_filenames if f not in source_md_text]
    assert not missing, f"Lottie files not listed in SOURCE.md: {missing}"


def test_only_permissive_licenses(source_md_text: str, lottie_filenames: list[str]) -> None:
    """Each table row mentioning a Lottie file must declare CC0 or MIT."""
    bad_rows: list[str] = []
    for raw_line in source_md_text.splitlines():
        line = raw_line.strip()
        if not line.startswith("|"):
            continue
        if not any(name in line for name in lottie_filenames):
            continue
        # Look for any allowed license token in this row.
        if not any(re.search(rf"\|\s*{re.escape(lic)}\s*\|", line) for lic in ALLOWED_LICENSES):
            bad_rows.append(line)
    assert not bad_rows, f"rows missing CC0/MIT license: {bad_rows}"


def test_no_forbidden_license_in_clip_rows(
    source_md_text: str, lottie_filenames: list[str]
) -> None:
    bad: list[str] = []
    for raw_line in source_md_text.splitlines():
        line = raw_line.strip()
        if not line.startswith("|"):
            continue
        if not any(name in line for name in lottie_filenames):
            continue
        for token in FORBIDDEN_LICENSE_TOKENS:
            if re.search(rf"\|\s*{token}[\w\.\-]*\s*\|", line, re.IGNORECASE):
                bad.append(line)
                break
    assert not bad, f"forbidden license tokens in Lottie rows: {bad}"


def test_each_row_has_sha256(source_md_text: str, lottie_filenames: list[str]) -> None:
    sha_re = re.compile(r"\b[a-fA-F0-9]{64}\b")
    for fname in lottie_filenames:
        row = next(
            (
                ln
                for ln in source_md_text.splitlines()
                if fname in ln and ln.strip().startswith("|")
            ),
            None,
        )
        assert row is not None, f"no SOURCE.md row for {fname}"
        assert sha_re.search(row), f"row for {fname} missing SHA256: {row!r}"


def test_sha256_matches_disk(lottie_filenames: list[str], source_md_text: str) -> None:
    """The SHA256 declared in SOURCE.md must match the file on disk byte-for-byte."""
    sha_re = re.compile(r"\b[a-fA-F0-9]{64}\b")
    for fname in lottie_filenames:
        row = next(
            (
                ln
                for ln in source_md_text.splitlines()
                if fname in ln and ln.strip().startswith("|")
            ),
            None,
        )
        assert row is not None
        match = sha_re.search(row)
        assert match is not None
        declared = match.group(0).lower()

        actual = hashlib.sha256((LOTTIE_DIR / fname).read_bytes()).hexdigest()
        assert declared == actual, (
            f"declared SHA256 for {fname} doesn't match disk:\n"
            f"  declared {declared}\n  actual   {actual}\n"
            "(if the generator changed, re-run scripts/generate_lottie_primitives.py "
            "and update SOURCE.md)"
        )
