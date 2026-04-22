# DEPLOYMENT.md — SkyHerd Vercel Deploy

## Prod URL

**https://skyherd-engine.vercel.app**

All three SPA routes verified live:
- `/` — main ranch dashboard (map + 5 agent lanes + cost ticker + attestation)
- `/rancher` — rancher phone PWA (Wes incoming call UI)
- `/cross-ranch` — two-ranch mesh view

## How it works

The deployed SPA runs in **replay demo mode** (`VITE_DEMO_MODE=replay`). On load it
fetches `/replay.json` (646 pre-recorded events across 5 scenarios) and replays them
at 3× speed through the same SSE handler code used in live mode. No backend required.

## Deploy from scratch

```bash
# 1. Install Vercel CLI (already at ~/.local/share/mise/installs/node/24.13.0/bin/vercel)
# 2. Link project (first time only)
cd web
vercel link --yes --project skyherd-engine

# 3. Set env var for production
echo "replay" | vercel env add VITE_DEMO_MODE production

# 4. Deploy
vercel --prod --yes
```

## Redeploy after code change

```bash
cd /home/george/projects/active/skyherd-engine/web
vercel --prod --yes
```

## Rollback

Option A — CLI:
```bash
vercel rollback
```

Option B — Dashboard: go to https://vercel.com/gandjbusiness/skyherd-engine/deployments,
find a previous deployment, click **Promote to Production**.

## Regenerate replay bundle

Run this whenever new scenario JSONL files are available (e.g. after `make demo SEED=42 SCENARIO=all`):

```bash
cd /home/george/projects/active/skyherd-engine
python3 scripts/build-replay.py
# Output: web/public/replay.json (5 scenarios, ~646 events, ~54 KB)
git add web/public/replay.json
git commit -m "chore: refresh replay bundle"
cd web && vercel --prod --yes
```

## Env vars

| Variable | Value | Environment | Notes |
|---|---|---|---|
| `VITE_DEMO_MODE` | `replay` | Production | Bakes replay mode into the SPA bundle |

Local dev (`make dashboard`) leaves `VITE_DEMO_MODE` unset — live FastAPI SSE at `/events`.

## Project info

- Vercel project: `gandjbusiness/skyherd-engine`
- Vercel inspect: https://vercel.com/gandjbusiness/skyherd-engine
- Build command: `pnpm install && pnpm run build`
- Output directory: `dist`
- Framework: Vite
- Root directory: `web/`
