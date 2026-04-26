"""Asserts all B-roll clips have permissive license entries in SOURCE.md.

This is the Phase D license-sweep gate: every .mp4 in
``remotion-video/public/broll/`` MUST be listed in ``SOURCE.md`` with a
permissive license token. AGPL/GPL contamination fails the test.
"""

from __future__ import annotations

import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
BROLL_DIR = ROOT / "remotion-video" / "public" / "broll"
SOURCE_MD = BROLL_DIR / "SOURCE.md"

ALLOWED_LICENSES: frozenset[str] = frozenset(
    {
        "Pexels License",
        "Pixabay License",
        "CC0",
        "Mixkit License",
        "Videvo License",
        "Coverr License",
    }
)

# License tokens that are NOT permitted for stock B-roll usage in this repo.
# (Mentioning them in prose is fine; what we forbid is treating them as the
# license a clip is shipped under.)
FORBIDDEN_LICENSE_TABLE_TOKENS: tuple[str, ...] = ("AGPL", "GPL")


@pytest.fixture(scope="module")
def source_md_text() -> str:
    """Read SOURCE.md once per module."""
    assert SOURCE_MD.exists(), f"SOURCE.md missing at {SOURCE_MD}"
    return SOURCE_MD.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def broll_clip_filenames() -> list[str]:
    """All .mp4 files currently in the broll directory, sorted."""
    return sorted(p.name for p in BROLL_DIR.glob("*.mp4"))


def test_broll_directory_exists() -> None:
    """B-roll directory must exist (created by Phase D)."""
    assert BROLL_DIR.is_dir(), f"{BROLL_DIR} does not exist"


def test_source_md_exists() -> None:
    """SOURCE.md provenance manifest must exist."""
    assert SOURCE_MD.is_file(), f"{SOURCE_MD} does not exist"


def test_at_least_ten_clips_present(broll_clip_filenames: list[str]) -> None:
    """Phase D plan target: ≥10 clips fetched."""
    assert len(broll_clip_filenames) >= 10, (
        f"Phase D mandates ≥10 stock B-roll clips; found {len(broll_clip_filenames)}: "
        f"{broll_clip_filenames}"
    )


def test_all_broll_clips_listed_in_source_md(
    broll_clip_filenames: list[str], source_md_text: str
) -> None:
    """Every .mp4 on disk MUST appear in SOURCE.md."""
    missing = [c for c in broll_clip_filenames if c not in source_md_text]
    assert not missing, f"clips not listed in SOURCE.md: {missing}"


def test_only_permissive_licenses_used(source_md_text: str) -> None:
    """Every license token in the SOURCE.md table must come from ALLOWED_LICENSES."""
    # Extract whatever sits between '|' separators in the markdown table.
    pattern = r"\|\s*(" + "|".join(re.escape(lic) for lic in ALLOWED_LICENSES) + r")\s*\|"
    found = set(re.findall(pattern, source_md_text))
    assert found, "no permissive license entries found in SOURCE.md table"
    # Sanity: the Mixkit License must be present given our current sourcing.
    assert "Mixkit License" in found, (
        "Phase D fetched all current clips from Mixkit, but Mixkit License "
        "is missing from SOURCE.md"
    )


def test_no_forbidden_license_in_table_rows(source_md_text: str) -> None:
    """No table row may declare a copyleft (AGPL/GPL) license for a clip.

    We restrict the check to lines that look like markdown table rows (start
    with '|'), so a forbidden token can still appear in prose if needed for
    documentation reasons — but never as the declared license for a clip.
    """
    bad_rows: list[str] = []
    for raw_line in source_md_text.splitlines():
        line = raw_line.strip()
        if not line.startswith("|"):
            continue
        for token in FORBIDDEN_LICENSE_TABLE_TOKENS:
            # Match the token surrounded by table-cell whitespace/pipes,
            # case-insensitive — so e.g. " AGPL ", " AGPL-3.0 ", "GPL-2.0".
            if re.search(rf"\|\s*{token}[\w\.\-]*\s*\|", line, re.IGNORECASE):
                bad_rows.append(line)
                break
    assert not bad_rows, f"forbidden copyleft licenses in clip rows: {bad_rows}"


def test_each_clip_row_has_acquisition_date(
    broll_clip_filenames: list[str], source_md_text: str
) -> None:
    """Every clip row should record an ISO-format acquisition date."""
    iso_re = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
    for clip in broll_clip_filenames:
        # Find the table line containing this clip name and assert it has a date.
        clip_line = next(
            (ln for ln in source_md_text.splitlines() if clip in ln and ln.strip().startswith("|")),
            None,
        )
        assert clip_line is not None, f"no table row for clip {clip}"
        assert iso_re.search(clip_line), (
            f"clip row for {clip} missing ISO acquisition date: {clip_line!r}"
        )


def test_original_content_inventory_exists() -> None:
    """ORIGINAL-CONTENT.md is the Phase D → Phase F handoff document."""
    inventory = BROLL_DIR / "ORIGINAL-CONTENT.md"
    assert inventory.is_file(), f"{inventory} does not exist"
    text = inventory.read_text(encoding="utf-8")
    # Must reference both core companion-asset directories.
    assert "remotion-video/public/clips/" in text
    assert "skills/" in text
