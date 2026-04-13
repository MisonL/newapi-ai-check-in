# Frontend Closure Review 2026-04-13

## Scope

- WebUI task-center front-end closure
- Empty-state guidance and disabled-state correctness
- Playwright smoke stability and local start path

## Changes Reviewed

- Removed obsolete route alias `web/pages/tasks-today.vue`
- Removed stale route title mapping from `web/app.vue`
- Kept `AppSelect` disabled behavior explicit for no-option states
- Added account-page empty-state guard and CTA path
- Added reports-page empty-state CTA path
- Stabilized Playwright startup and local `start` command
- Updated README current WebUI scope and validation commands

## Validation Commands

```bash
cd web && npm run build
cd web && npm run test:e2e
uv run pytest -q
```

## Expected Gate

- `npm run build` exits `0`
- `npm run test:e2e` exits `0`
- `uv run pytest -q` exits `0`

## Notes

- `npm run test:e2e` now supports two modes:
  - default mode: Playwright starts backend and frontend test services automatically
  - external mode: `PLAYWRIGHT_EXTERNAL_SERVER=1 npm run test:e2e`
- The default `start` path now uses `.output/server/index.mjs`, avoiding the previous unstable `nuxt start --host ...` path in this repository.
