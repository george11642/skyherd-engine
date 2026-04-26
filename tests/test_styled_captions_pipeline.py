"""Phase G — Opus 4.7 AI-directed caption styling pipeline tests.

These tests anchor the contract for the ``style`` sub-command of
``scripts/generate_kinetic_captions.py``: it reads the variant's
``captions-{A,B,C}.json`` plus the variant script, asks Claude Opus 4.7
to emit per-word visual styling, and writes
``styled-captions-{A,B,C}.json``.

We do NOT call the live Anthropic API in these tests — that is gated
behind ``make video-style-captions`` in the Makefile. Instead we exercise:

  * the pure helpers that build the user prompt and parse the styled
    JSON response (deterministic, fast),
  * the on-disk schema (every word has the required fields, valid
    enums, hex colors, level in range),
  * the fixture at ``tests/fixtures/captions/sample-styled.json``
    (representative output the component test can use as a stand-in
    for real Opus output).
"""

from __future__ import annotations

import json
import pathlib
import re
from typing import Any

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
GENERATOR = SCRIPTS_DIR / "generate_kinetic_captions.py"
FIXTURES_DIR = ROOT / "tests" / "fixtures" / "captions"
SAMPLE_STYLED = FIXTURES_DIR / "sample-styled.json"
CAPTIONS_DIR = ROOT / "remotion-video" / "public" / "captions"

ALLOWED_ANIMATIONS = {"fade", "pop", "pulse", "scale", "glow"}
ALLOWED_WEIGHTS = {"normal", "bold", "black"}
HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


# --------------------------------------------------------------------------- #
# Module loader (mirrors test_kinetic_captions_pipeline.py)                   #
# --------------------------------------------------------------------------- #


def _load_kc_module() -> Any:
    import importlib.util
    import sys as _sys

    spec = importlib.util.spec_from_file_location("kc_generator", GENERATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    _sys.modules["kc_generator"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def kc_module() -> Any:
    return _load_kc_module()


# --------------------------------------------------------------------------- #
# Public API surface (style sub-command)                                      #
# --------------------------------------------------------------------------- #


def test_style_sub_command_helpers_exist(kc_module: Any) -> None:
    """Generator must expose the helpers the styled pipeline needs."""
    for name in (
        "flatten_caption_words",
        "build_style_user_prompt",
        "parse_styled_response",
        "build_style_payload",
        "STYLE_SYSTEM_PROMPT",
        "STYLE_PALETTE",
    ):
        assert hasattr(kc_module, name), f"missing public symbol: {name}"


def test_style_palette_contains_required_swatches(kc_module: Any) -> None:
    """Earth-tone palette must include the warm cream, espresso, clay,
    sage, and brick swatches called out in the system prompt."""
    palette = set(c.lower() for c in kc_module.STYLE_PALETTE)
    for hex_value in ("#f5d49c", "#5a3a22", "#a36b3a", "#3d5a3d", "#c04b2d"):
        assert hex_value in palette, f"palette missing {hex_value}"


def test_style_system_prompt_mentions_emphasis_and_palette(kc_module: Any) -> None:
    sp = kc_module.STYLE_SYSTEM_PROMPT
    assert "emphasis_level" in sp, "system prompt must explain emphasis_level"
    assert "0" in sp and "3" in sp, "system prompt must specify the 0-3 range"
    for animation in ALLOWED_ANIMATIONS:
        assert animation in sp, f"system prompt must list animation '{animation}'"


# --------------------------------------------------------------------------- #
# flatten_caption_words — sparse + dense input shapes                         #
# --------------------------------------------------------------------------- #


def test_flatten_caption_words_sparse(kc_module: Any) -> None:
    """Sparse captions (variants A/B) — emphasis windows become single
    pseudo-words preserving second-as-start with a small dwell."""
    payload = {
        "variant": "A",
        "mode": "sparse",
        "emphasis": [
            {"second": 1, "text": "Everyone thinks"},
            {"second": 4, "text": "They don't."},
        ],
        "segments": [],
    }
    words = kc_module.flatten_caption_words(payload)
    assert len(words) == 4  # "Everyone","thinks","They","don't."
    assert words[0]["word"] == "Everyone"
    assert words[0]["start"] == pytest.approx(1.0)
    assert words[0]["segment_id"] == 0
    assert words[2]["segment_id"] == 1


def test_flatten_caption_words_dense(kc_module: Any) -> None:
    """Dense captions (variant C) — every word becomes its own entry,
    segment_id derives from the source segment index."""
    payload = {
        "variant": "C",
        "mode": "dense",
        "emphasis": [],
        "segments": [
            {
                "start": 0.0,
                "end": 0.6,
                "text": "Skyherd watches.",
                "words": [
                    {"word": "Skyherd", "start": 0.0, "end": 0.3},
                    {"word": "watches.", "start": 0.3, "end": 0.6},
                ],
            },
            {
                "start": 0.7,
                "end": 1.2,
                "text": "Every fence.",
                "words": [
                    {"word": "Every", "start": 0.7, "end": 0.9},
                    {"word": "fence.", "start": 0.9, "end": 1.2},
                ],
            },
        ],
    }
    words = kc_module.flatten_caption_words(payload)
    assert [w["word"] for w in words] == ["Skyherd", "watches.", "Every", "fence."]
    assert words[0]["segment_id"] == 0
    assert words[3]["segment_id"] == 1


# --------------------------------------------------------------------------- #
# Prompt construction                                                         #
# --------------------------------------------------------------------------- #


def test_build_style_user_prompt_embeds_variant_and_words(kc_module: Any) -> None:
    words = [
        {"word": "Everyone", "start": 0.12, "end": 0.45, "segment_id": 0},
        {"word": "thinks", "start": 0.45, "end": 0.78, "segment_id": 0},
    ]
    prompt = kc_module.build_style_user_prompt(
        variant="A",
        words=words,
        script_excerpt="# Script A — winner pattern\nCold open: Everyone thinks…",
    )
    assert "Variant: A" in prompt
    assert "Everyone" in prompt
    # The word-level JSON must be inline so Opus sees timestamps + ordering.
    assert '"word": "Everyone"' in prompt or '"word":"Everyone"' in prompt
    assert "JSON" in prompt.upper()


# --------------------------------------------------------------------------- #
# Response parsing                                                            #
# --------------------------------------------------------------------------- #


@pytest.fixture
def sample_words() -> list[dict[str, Any]]:
    return [
        {"word": "Everyone", "start": 0.0, "end": 0.4, "segment_id": 0},
        {"word": "blind.", "start": 4.1, "end": 4.5, "segment_id": 1},
    ]


def test_parse_styled_response_strict_json(
    kc_module: Any, sample_words: list[dict[str, Any]]
) -> None:
    """The parser accepts the exact JSON-array shape Opus is asked to emit."""
    raw = json.dumps(
        [
            {
                "word": "Everyone",
                "start": 0.0,
                "end": 0.4,
                "segment_id": 0,
                "color": "#F5D49C",
                "weight": "bold",
                "animation": "fade",
                "emphasis_level": 1,
            },
            {
                "word": "blind.",
                "start": 4.1,
                "end": 4.5,
                "segment_id": 1,
                "color": "#C04B2D",
                "weight": "black",
                "animation": "glow",
                "emphasis_level": 3,
            },
        ]
    )
    parsed = kc_module.parse_styled_response(raw, source_words=sample_words)
    assert len(parsed) == 2
    assert parsed[0]["color"] == "#F5D49C"
    assert parsed[1]["animation"] == "glow"


def test_parse_styled_response_strips_code_fence(
    kc_module: Any, sample_words: list[dict[str, Any]]
) -> None:
    """If Opus wraps output in ```json fences, the parser tolerates it."""
    inner = json.dumps(
        [
            {
                "word": "Everyone",
                "start": 0.0,
                "end": 0.4,
                "segment_id": 0,
                "color": "#F5D49C",
                "weight": "bold",
                "animation": "fade",
                "emphasis_level": 1,
            },
            {
                "word": "blind.",
                "start": 4.1,
                "end": 4.5,
                "segment_id": 1,
                "color": "#C04B2D",
                "weight": "black",
                "animation": "glow",
                "emphasis_level": 3,
            },
        ]
    )
    raw = f"```json\n{inner}\n```"
    parsed = kc_module.parse_styled_response(raw, source_words=sample_words)
    assert len(parsed) == 2


def test_parse_styled_response_rejects_count_mismatch(
    kc_module: Any, sample_words: list[dict[str, Any]]
) -> None:
    """Opus must return exactly one styled entry per source word."""
    raw = json.dumps(
        [
            {
                "word": "Everyone",
                "start": 0.0,
                "end": 0.4,
                "segment_id": 0,
                "color": "#F5D49C",
                "weight": "bold",
                "animation": "fade",
                "emphasis_level": 1,
            }
        ]
    )
    with pytest.raises(ValueError, match="(?i)word count"):
        kc_module.parse_styled_response(raw, source_words=sample_words)


def test_parse_styled_response_rejects_bad_animation(
    kc_module: Any, sample_words: list[dict[str, Any]]
) -> None:
    raw = json.dumps(
        [
            {
                "word": "Everyone",
                "start": 0.0,
                "end": 0.4,
                "segment_id": 0,
                "color": "#F5D49C",
                "weight": "bold",
                "animation": "explode",  # not in the allow-set
                "emphasis_level": 1,
            },
            {
                "word": "blind.",
                "start": 4.1,
                "end": 4.5,
                "segment_id": 1,
                "color": "#C04B2D",
                "weight": "black",
                "animation": "glow",
                "emphasis_level": 3,
            },
        ]
    )
    with pytest.raises(ValueError, match="(?i)animation"):
        kc_module.parse_styled_response(raw, source_words=sample_words)


# --------------------------------------------------------------------------- #
# Payload + on-disk schema                                                    #
# --------------------------------------------------------------------------- #


def test_build_style_payload_round_trips(kc_module: Any) -> None:
    styled_words = [
        {
            "word": "Everyone",
            "start": 0.0,
            "end": 0.4,
            "segment_id": 0,
            "color": "#F5D49C",
            "weight": "bold",
            "animation": "fade",
            "emphasis_level": 1,
        }
    ]
    payload = kc_module.build_style_payload(
        variant="A", model="claude-opus-4-7", words=styled_words
    )
    assert payload["variant"] == "A"
    assert payload["mode"] == "styled"
    assert payload["model"] == "claude-opus-4-7"
    assert payload["words"] == styled_words
    assert "fingerprint" in payload and isinstance(payload["fingerprint"], str)
    # Round trip through JSON.
    restored = json.loads(json.dumps(payload))
    assert restored == payload


# --------------------------------------------------------------------------- #
# Fixture schema (component fallback test ammo)                               #
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def fixture_payload() -> dict[str, Any]:
    assert SAMPLE_STYLED.is_file(), f"missing fixture: {SAMPLE_STYLED}"
    return json.loads(SAMPLE_STYLED.read_text(encoding="utf-8"))


def test_fixture_has_required_top_level_keys(
    fixture_payload: dict[str, Any],
) -> None:
    for key in ("variant", "mode", "model", "fingerprint", "words"):
        assert key in fixture_payload, f"fixture missing {key}"


def test_fixture_each_word_has_required_fields(
    fixture_payload: dict[str, Any],
) -> None:
    required = (
        "word",
        "start",
        "end",
        "segment_id",
        "color",
        "weight",
        "animation",
        "emphasis_level",
    )
    for entry in fixture_payload["words"]:
        for field in required:
            assert field in entry, f"word missing {field}: {entry}"


def test_fixture_color_is_hex(fixture_payload: dict[str, Any]) -> None:
    for entry in fixture_payload["words"]:
        assert HEX_RE.match(entry["color"]), f"bad hex: {entry['color']}"


def test_fixture_emphasis_level_in_range(
    fixture_payload: dict[str, Any],
) -> None:
    for entry in fixture_payload["words"]:
        level = entry["emphasis_level"]
        assert isinstance(level, int)
        assert 0 <= level <= 3, f"emphasis_level out of range: {level}"


def test_fixture_animation_in_allowed_set(
    fixture_payload: dict[str, Any],
) -> None:
    for entry in fixture_payload["words"]:
        assert entry["animation"] in ALLOWED_ANIMATIONS, f"bad animation: {entry['animation']}"


def test_fixture_weight_in_allowed_set(
    fixture_payload: dict[str, Any],
) -> None:
    for entry in fixture_payload["words"]:
        assert entry["weight"] in ALLOWED_WEIGHTS, f"bad weight: {entry['weight']}"


def test_fixture_has_emphasis_3_examples(
    fixture_payload: dict[str, Any],
) -> None:
    """The hand-authored fixture should demonstrate at least one
    emphasis_level=3 word, since component tests rely on that case."""
    has_three = any(w["emphasis_level"] == 3 for w in fixture_payload["words"])
    assert has_three, "fixture must include at least one emphasis_level=3 word"


# --------------------------------------------------------------------------- #
# Output path + word-count parity per variant                                 #
# --------------------------------------------------------------------------- #


def test_styled_output_path_helper(kc_module: Any) -> None:
    """The generator exposes a styled-output-path helper used by
    ``make video-style-captions`` and the run loop."""
    assert hasattr(kc_module, "styled_output_path")
    p = kc_module.styled_output_path("A")
    assert p.name == "styled-captions-A.json"
    assert p.parent == CAPTIONS_DIR


def test_styled_output_word_count_matches_input_when_present(
    kc_module: Any,
) -> None:
    """For every variant whose styled JSON has been generated, every
    input caption word must have exactly one styled entry. We skip
    variants that haven't been run yet (style-step is gated behind
    ``make video-style-captions`` and ``ANTHROPIC_API_KEY``)."""
    for variant in ("A", "B", "C"):
        styled = CAPTIONS_DIR / f"styled-captions-{variant}.json"
        if not styled.is_file():
            continue
        plain = CAPTIONS_DIR / f"captions-{variant}.json"
        assert plain.is_file(), (
            f"styled-captions-{variant}.json exists but captions-{variant}.json missing"
        )
        plain_payload = json.loads(plain.read_text(encoding="utf-8"))
        styled_payload = json.loads(styled.read_text(encoding="utf-8"))
        expected = len(kc_module.flatten_caption_words(plain_payload))
        actual = len(styled_payload.get("words", []))
        assert expected == actual, (
            f"variant {variant}: caption words ({expected}) != styled words ({actual})"
        )


# --------------------------------------------------------------------------- #
# Component fallback contract (schema-only — Remotion isn't loaded here)      #
# --------------------------------------------------------------------------- #


def test_kinetic_captions_renders_falls_back_to_plain_when_styled_missing() -> None:
    """KineticCaptions.tsx must keep the plain captions path working
    when the styled JSON isn't on disk. We assert the on-disk shape
    contracts that enable that fallback:

      * plain captions still expose ``mode: 'sparse'|'dense'`` and
        ``emphasis``/``segments`` arrays the existing component reads,
      * the styled JSON uses a different filename (no overlap), so a
        missing styled file leaves the plain fetch untouched.
    """
    # Plain captions (always present after Phase E1).
    for variant in ("A", "B", "C"):
        plain = CAPTIONS_DIR / f"captions-{variant}.json"
        assert plain.is_file(), f"plain captions missing for {variant}"
        payload = json.loads(plain.read_text(encoding="utf-8"))
        assert payload["mode"] in ("sparse", "dense")
        assert "emphasis" in payload
        assert "segments" in payload

    # Styled captions live at a distinct path — fallback works because
    # the component fetches the styled URL first, then falls back on
    # 404/parse-error to the plain URL.
    styled_paths = {CAPTIONS_DIR / f"styled-captions-{v}.json" for v in "ABC"}
    plain_paths = {CAPTIONS_DIR / f"captions-{v}.json" for v in "ABC"}
    assert styled_paths.isdisjoint(plain_paths)
