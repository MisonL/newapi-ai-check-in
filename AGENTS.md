# Repository Guidelines

## Project Structure & Module Organization

- `control_plane/`: FastAPI control plane, schedulers, storage, API routes, and executors.
- `web/`: Nuxt 3 WebUI with pages, components, composables, and locale files.
- `tests/`: Python service and API tests such as `test_control_plane_api.py`.
- `scripts/`: local helper scripts for starting and validating the stack.
- `assets/`, `docs/architecture/`, `docs/superpowers/`, `secret-json-generator.html`: static assets, durable design docs, Superpowers specs/plans, and config helpers.

Keep backend changes inside `control_plane/` and UI changes inside `web/`. Avoid unrelated refactors in the same change.

## Build, Test, and Development Commands

- `uv sync --dev`: install Python dependencies into `.venv`.
- `.venv/bin/pytest tests/test_control_plane_api.py tests/test_job_service.py`: run focused backend tests.
- `.venv/bin/ruff check .`: run Python lint checks.
- `npm --prefix web install`: install WebUI dependencies.
- `npm --prefix web run dev`: start the Nuxt development server.
- `npm --prefix web run build`: create the production WebUI build.
- `HOST_PORT=3300 docker compose up -d --build`: run the full stack locally.
- `gh run list --repo MisonL/newapi-ai-check-in --workflow CI --limit 3`: inspect recent CI results.

Wait for `docker compose ps` to report `healthy` before opening the UI.

## Coding Style & Naming Conventions

- Python follows `pyproject.toml`: 120-char lines, single quotes, and tab indentation via Ruff format.
- Vue/TypeScript follows the existing Nuxt style: `script setup`, typed composables, and small computed helpers.
- Use descriptive names such as `deploy_mode`, `scheduler_enabled`, and `saveSchedule`.
- Prefer explicit errors over hidden fallback behavior.

## Testing Guidelines

- Backend tests use `pytest`; add new tests under `tests/` with names like `test_<feature>.py`.
- For any code or behavior change, follow TDD: write the smallest failing test first, run it and confirm the expected failure, implement the minimal change, then rerun the test.
- For UI changes, always run `npm --prefix web run build`; verify affected pages in the browser when behavior changes.
- GitHub CI runs Ruff, all backend tests, Nuxt build, and Playwright E2E on `main` pushes and pull requests.

## Superpowers Workflow

- Start every task with `superpowers:using-superpowers` to check applicable skills before acting.
- Use `superpowers:test-driven-development` for implementation, refactors, and bug fixes.
- Follow Red-Green-Refactor: add the smallest failing test, confirm the expected failure, implement the minimum change, then rerun the test.
- Use `superpowers:systematic-debugging` for failures or unexpected behavior.
- Use `superpowers:verification-before-completion` before claiming work is complete, committing, or pushing.
- Keep generated reviews, screenshots, Playwright output, caches, and temporary artifacts out of the repository. Use ignored local paths only.

## Commit & Pull Request Guidelines

- Match existing commit style: `feat: ...`, `fix: ...`, `ci(...): ...`, `chore(...): ...`.
- Keep commits scoped to one logical change.
- PRs should include the purpose, affected modules, validation commands, and screenshots for visible UI updates.

## Security & Configuration Tips

- Never commit real secrets. Use `.env.example`, `.env.control-plane.example`, and `.env.github-actions.example` as templates.
- Choose exactly one deployment mode: `CONTROL_PLANE_DEPLOY_MODE=control_plane` or `github_actions`.
