"""A1 live probe — verify that ``extra_body={"resources": [{"type":"memory_store", ...}]}``
works end-to-end against the live Anthropic Managed Agents API.

Outputs one of four statuses to ``docs/A1_PROBE_RESULT.md``:
  - PASS:                extra_body path accepted + memory_store attach echoed.
  - FAIL_USE_RAW_POST:   extra_body rejected with message mentioning resources/memory_store.
  - UNCLEAR:             extra_body accepted but attach NOT echoed in response.
  - SKIPPED:             ANTHROPIC_API_KEY unset.

Fully self-cleaning — archives the probe memstore + agent + environment in a ``finally`` block.
Redacts ``apikey_*`` substrings from the written doc before persisting.

Usage:
    uv run python scripts/a1_probe.py
"""

from __future__ import annotations

import asyncio
import os
import re
import secrets
from pathlib import Path
from typing import Any

# The anthropic SDK's `cast_to` expects a parameterized generic like Dict[str, Any]
# — bare `dict` breaks `construct_type` at `get_args(type_)`.
_RESP = dict[str, Any]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BETA_HEADER = {"anthropic-beta": "managed-agents-2026-04-01"}
APIKEY_REDACT = re.compile(r"apikey_[A-Za-z0-9]+")


def _redact(text: str) -> str:
    return APIKEY_REDACT.sub("apikey_REDACTED", text)


def _write_doc(status: str, body: str) -> None:
    doc = Path("docs/A1_PROBE_RESULT.md")
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text(_redact(body))


SKIPPED_BODY = """\
---
status: SKIPPED
probe_run_at: unknown
---

# A1 Probe Result — SKIPPED

`ANTHROPIC_API_KEY` was not set when the probe ran. The A1 assumption
(`extra_body={"resources": [{"type":"memory_store", ...}]}` accepted by
`client.beta.sessions.create(...)`) remains **ASSUMED** — Plan 01-03 should use
the `extra_body` path untested, with a warning in its SUMMARY that A1 was not
live-verified.

## Fallback plan

If integration testing later reveals A1 is rejected, Plan 01-03 Task 2 must
switch to raw HTTP:

```python
resp = await self._client.post(
    "/v1/sessions",
    cast_to=dict,
    body={"agent": agent_id, "environment_id": env_id, "title": ..., "resources": resources},
    options={"headers": {"anthropic-beta": "managed-agents-2026-04-01"}},
)
```

Set the env var and re-run `uv run python scripts/a1_probe.py` whenever an API
key is available to promote this status to PASS or FAIL.
"""


# ---------------------------------------------------------------------------
# Probe
# ---------------------------------------------------------------------------


async def _run_probe() -> None:
    import anthropic  # noqa: PLC0415 — lazy import so SKIPPED path needs no dep.

    suffix = secrets.token_hex(4)  # 8 hex chars — collision-free probe name
    probe_name = f"a1_probe_{suffix}"

    client = anthropic.AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    memstore_id: str | None = None
    agent_id: str | None = None
    env_id: str | None = None

    session_response: dict | None = None
    session_error: str | None = None

    try:
        # 1a. Create memstore.
        memstore = await client.post(
            "/v1/memory_stores",
            cast_to=_RESP,
            body={
                "name": probe_name,
                "description": "A1 assumption probe — archive immediately",
            },
            options={"headers": BETA_HEADER},
        )
        memstore_id = memstore["id"]
        assert isinstance(memstore_id, str) and memstore_id.startswith("memstore_"), (
            f"Expected memstore_ prefix, got: {memstore_id!r}"
        )

        # 1b. Write one memory (confirm memver_ prefix shape).
        memory = await client.post(
            f"/v1/memory_stores/{memstore_id}/memories",
            cast_to=_RESP,
            body={"path": "/a1/probe.md", "content": "A1 probe content"},
            options={"headers": BETA_HEADER},
        )
        memver_id = memory.get("memory_version_id", "")
        assert memver_id.startswith("memver_"), f"Expected memver_ prefix, got: {memver_id!r}"

        # 1c. Create agent.
        agent = await client.post(
            "/v1/agents",
            cast_to=_RESP,
            body={"name": f"{probe_name}_agent", "model": "claude-sonnet-4-5"},
            options={"headers": BETA_HEADER},
        )
        agent_id = agent["id"]

        # 1d. Create environment.
        env = await client.post(
            "/v1/environments",
            cast_to=_RESP,
            body={"name": f"{probe_name}_env"},
            options={"headers": BETA_HEADER},
        )
        env_id = env["id"]

        # 1e. The A1 assumption: session.create with extra_body resources.
        try:
            session_obj = await client.beta.sessions.create(
                agent=agent_id,
                environment_id=env_id,
                title=probe_name,
                extra_body={
                    "resources": [
                        {
                            "type": "memory_store",
                            "memory_store_id": memstore_id,
                            # NOTE: `mode` field previously caused 400 "Extra inputs not permitted"
                            # per probe run 2026-04-23. Omitted here — attach is read_write by default
                            # (or the server rejects the whole attach if ambiguous).
                        }
                    ],
                },
            )
            # Try to serialize to dict for echoing.
            try:
                session_response = session_obj.model_dump()  # pydantic v2
            except AttributeError:
                session_response = (
                    dict(session_obj)
                    if hasattr(session_obj, "__iter__")
                    else {
                        "id": getattr(session_obj, "id", None),
                        "raw": str(session_obj),
                    }
                )
        except Exception as exc:  # noqa: BLE001
            session_error = f"{type(exc).__name__}: {exc!s}"

        # 2. Branch.
        if session_error is not None:
            msg_lower = session_error.lower()
            if any(
                tok in msg_lower
                for tok in ("resources", "memory_store", "unknown", "invalid", "not recognized")
            ):
                status = "FAIL_USE_RAW_POST"
                directive = (
                    'Plan 01-03 MUST switch to raw `client.post("/v1/sessions", body={'
                    "agent, environment_id, title, resources:[...]})` with headers "
                    '`{"anthropic-beta": "managed-agents-2026-04-01"}`.'
                )
                body = f"""\
---
status: FAIL_USE_RAW_POST
---

# A1 Probe Result — FAIL (extra_body rejected)

The `client.beta.sessions.create(extra_body={{"resources": [...]}})` call was
rejected by the Anthropic API.

## Error

```
{session_error}
```

## Directive

{directive}

## Probe state

- Memstore (archived): `{memstore_id}`
- Agent: `{agent_id}`
- Environment: `{env_id}`
"""
                stdout_token = "A1_PROBE_FAIL_USE_RAW_POST"
            else:
                # Unrelated error — treat as UNCLEAR, propagate.
                status = "UNCLEAR"
                body = f"""\
---
status: UNCLEAR
---

# A1 Probe Result — UNCLEAR

The probe failed in an unexpected way (not a resources/memory_store rejection):

```
{session_error}
```

Re-run the probe or escalate. Plan 01-03 should default to the `extra_body`
path with a warning.
"""
                stdout_token = "A1_PROBE_UNCLEAR"
        else:
            # Successful 2xx — check if memory_store attached in response.
            raw = str(session_response or "")
            attached = ("memory_store" in raw) or (memstore_id in raw)
            if attached:
                status = "PASS"
                body = f"""\
---
status: PASS
---

# A1 Probe Result — PASS

`client.beta.sessions.create(extra_body={{"resources": [{{"type":"memory_store", ...}}]}})`
was accepted by the live Anthropic API and the memory_store attachment
appears in the response payload.

## Probe state (archived)

- Memstore: `{memstore_id}`
- Agent: `{agent_id}`
- Environment: `{env_id}`

## Response echo (sanitized, apikey_* redacted)

```
{raw[:2000]}
```

## Known schema notes (discovered during probe)

- The field name for read/write permissions on a memory_store resource is
  **`access`**, NOT `mode`. Sending `"mode": "read_write"` triggers a 400
  with `"resources.0.mode: Extra inputs are not permitted"`.
- Live API echoes back `'access': 'read_write'` by default when neither field
  is sent, i.e. the attach defaults to read_write.
- The `path` field on memory writes MUST start with `/` (validated against
  regex `^(/[^/\x00]+)+$`).

## Directive

Plan 01-03 proceeds on the **extra_body** path. No raw-POST fallback needed.
Plan 01-03 MUST use the field name `"access"` (not `"mode"`) when differentiating
read_only vs read_write. Alternatively, omit the field entirely to default to
read_write — acceptable for per-agent stores, but for the shared domain library
the `"access": "read_only"` key is required.
"""
                stdout_token = "A1_PROBE_PASS"
            else:
                status = "UNCLEAR"
                body = f"""\
---
status: UNCLEAR
---

# A1 Probe Result — UNCLEAR (attach accepted but not echoed)

The API returned 2xx but the memory_store attachment does NOT appear in the
session-create response body. The extra_body path may silently ignore unknown
fields.

## Response echo (sanitized, apikey_* redacted)

```
{raw[:2000]}
```

## Probe state (archived)

- Memstore: `{memstore_id}`
- Agent: `{agent_id}`
- Environment: `{env_id}`

## Directive

Plan 01-04 MUST verify attach via `memory_versions.list()` or by listing
session events / session config retrieval after the first wake cycle.
"""
                stdout_token = "A1_PROBE_UNCLEAR"

        _write_doc(status, body)
        print(stdout_token)

    finally:
        # Best-effort cleanup — do NOT fail the probe if these 404.
        if memstore_id:
            try:
                await client.post(
                    f"/v1/memory_stores/{memstore_id}/archive",
                    cast_to=_RESP,
                    body={},
                    options={"headers": BETA_HEADER},
                )
            except Exception:  # noqa: BLE001
                pass
        if agent_id:
            try:
                await client.post(
                    f"/v1/agents/{agent_id}/archive",
                    cast_to=_RESP,
                    body={},
                    options={"headers": BETA_HEADER},
                )
            except Exception:  # noqa: BLE001
                pass
        if env_id:
            try:
                await client.post(
                    f"/v1/environments/{env_id}/archive",
                    cast_to=_RESP,
                    body={},
                    options={"headers": BETA_HEADER},
                )
            except Exception:  # noqa: BLE001
                pass


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        _write_doc("SKIPPED", SKIPPED_BODY)
        print("A1_PROBE_SKIPPED: no ANTHROPIC_API_KEY set — A1 remains ASSUMED")
        return
    try:
        asyncio.run(_run_probe())
    except Exception as exc:  # noqa: BLE001
        # Probe itself crashed — record as UNCLEAR.
        import traceback

        tb = traceback.format_exc()
        _write_doc(
            "UNCLEAR",
            f"""\
---
status: UNCLEAR
---

# A1 Probe Result — UNCLEAR (probe crash)

```
{type(exc).__name__}: {exc!s}
```

## Traceback

```
{tb}
```

Probe crashed before determining A1 status. Re-run once the environment is
healthy. Plan 01-03 defaults to the `extra_body` path with a warning.
""",
        )
        print("A1_PROBE_UNCLEAR")


if __name__ == "__main__":
    main()
