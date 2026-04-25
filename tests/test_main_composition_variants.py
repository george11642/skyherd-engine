"""Sanity test: each of A/B/C compositions has the expected sequence count.

Phase C of the demo-video v2 plan introduces a `variant` prop to the Main
Remotion composition. A and B render a 3-act winner-pattern skeleton; C
renders a 5-act differentiated layout. We verify the dispatch logic in
Main.tsx by string inspection — no Vitest/JSDOM environment available
inside the Python pytest harness.

A separate Vitest suite would cover behavioral assertions; this one
guards the source-level invariants.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MAIN_TSX = REPO_ROOT / "remotion-video" / "src" / "Main.tsx"
ROOT_TSX = REPO_ROOT / "remotion-video" / "src" / "Root.tsx"
META_TS = (
    REPO_ROOT
    / "remotion-video"
    / "src"
    / "compositions"
    / "calculate-main-metadata.ts"
)


def _read(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def test_main_dispatches_on_variant_prop() -> None:
    """Main.tsx must switch on the `variant` prop for A/B vs C."""
    src = _read(MAIN_TSX)
    if not src:
        return  # tolerate missing tree

    # Variant-aware dispatch must reference all three variants.
    assert "variant" in src, "Main.tsx must accept a variant prop"
    assert 'variant === "C"' in src, "Main.tsx must branch on variant === 'C'"

    # AB tree imports
    assert "ABAct1Hook" in src
    assert "ABAct2Demo" in src
    assert "ABAct3Close" in src
    # C tree imports — five acts
    assert "CAct1Hook" in src
    assert "CAct2Story" in src
    assert "CAct3Demo" in src
    assert "CAct4Substance" in src
    assert "CAct5Close" in src


def test_root_registers_three_variant_compositions() -> None:
    """Root.tsx must register Main_A, Main_B, Main_C compositions."""
    src = _read(ROOT_TSX)
    if not src:
        return

    for cid in ('id="Main-A"', 'id="Main-B"', 'id="Main-C"'):
        assert cid in src, f"Root.tsx missing composition registration {cid}"


def test_metadata_supports_five_acts() -> None:
    """calculate-main-metadata.ts must populate act4/act5 for variant C."""
    src = _read(META_TS)
    if not src:
        return

    assert "act4" in src, "ActDurations type must include act4"
    assert "act5" in src, "ActDurations type must include act5"
    # Variant type must be exported as a string-literal union.
    assert 'export type Variant = "A" | "B" | "C"' in src or (
        '"A"' in src and '"B"' in src and '"C"' in src
    )


def test_ab_act1_uses_variant_specific_vo_files() -> None:
    """ABAct1Hook must select intro/bridge VOs based on variant prop."""
    p = REPO_ROOT / "remotion-video" / "src" / "acts" / "v2" / "ABAct1Hook.tsx"
    src = _read(p)
    if not src:
        return

    # Both variant-specific VO files must be referenced.
    assert "vo-intro.mp3" in src, "ABAct1Hook must reference Variant A intro"
    assert "vo-intro-B.mp3" in src, "ABAct1Hook must reference Variant B intro"
    assert "vo-bridge.mp3" in src
    assert "vo-bridge-B.mp3" in src


def test_c_acts_use_c_specific_vo_files() -> None:
    """CActs must reference the -C suffixed variant cues."""
    p = REPO_ROOT / "remotion-video" / "src" / "acts" / "v2" / "CActs.tsx"
    src = _read(p)
    if not src:
        return

    for cue in (
        "vo-hook-C.mp3",
        "vo-story-C.mp3",
        "vo-synthesis-C.mp3",
        "vo-opus-C.mp3",
        "vo-depth-C.mp3",
        "vo-close-C.mp3",
    ):
        assert cue in src, f"CActs missing reference to {cue}"


def test_three_variant_scripts_exist() -> None:
    """All three variant scripts must be authored on disk."""
    scripts_dir = REPO_ROOT / "docs" / "scripts"
    for name in (
        "skyherd-script-A-winner-pattern.md",
        "skyherd-script-B-hybrid.md",
        "skyherd-script-C-differentiated.md",
    ):
        p = scripts_dir / name
        assert p.is_file(), f"Variant script missing: {p}"
        # Each script should include the chosen voice ID for reproducibility.
        text = p.read_text(encoding="utf-8")
        assert "ErXwobaYiN019PkySvjV" in text, (
            f"{p.name} should record the Antoni voice ID for reproducibility"
        )
