# di-integration — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps
> use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `modern-di-aiohttp`, the modern-di integration for aiohttp —
`setup_di`/`fetch_di_container` wiring, per-connection scoped child containers
(HTTP=`Scope.REQUEST`, WebSocket=`Scope.SESSION`), and the `FromDI`/`@inject`
resolution path — at repo parity with `modern-di-starlette`.

**Spec:** [`design.md`](./design.md)

**Branch:** `main` (this is a greenfield repo; Tasks 1-5 land directly on
`main` as per-task commits, no feature branch).

**Commit strategy:** Per-task commits.

---

### Task 1: Repo scaffolding and empty package

**Files:**
- Create dir `modern-di-aiohttp`, `git init`.
- Copy from `modern-di-starlette` (verbatim): `Justfile`, `LICENSE`,
  `.gitignore`, `.github/` (whole tree), `planning/` (whole tree).
- Create: `pyproject.toml`, `README.md`, `CLAUDE.md`,
  `modern_di_aiohttp/__init__.py`, `modern_di_aiohttp/main.py`,
  `modern_di_aiohttp/py.typed`, `tests/__init__.py`.

Scaffold the repo skeleton by copying tooling from the sibling and editing
names, plus an importable empty package, so `just install` and `just lint-ci`
pass before any DI logic exists.

- [x] **Step 1: Land the scaffold**

  Commits `1ba0b33` (scaffold), `d9c5dbf` (replace stale
  `modern-di-starlette` references with `modern-di-aiohttp`).

---

### Task 2: Connection providers, container wiring, and per-connection middleware

**Files:**
- Modify: `modern_di_aiohttp/main.py`, `modern_di_aiohttp/__init__.py`
- Create: `tests/dependencies.py`, `tests/conftest.py`,
  `tests/test_lifespan.py`, `tests/test_middleware.py`

Wire the root container into the aiohttp app (`setup_di`/`fetch_di_container`),
open/close it on the app's startup/cleanup signals, and build a scoped child
container per connection — HTTP opens `Scope.REQUEST`; a WebSocket-upgrade
request (detected via `can_prepare`) opens `Scope.SESSION`.

- [x] **Step 1: Land the wiring**

  Commit `ec741c7` — "feat: wire container into aiohttp with per-connection
  middleware".

---

### Task 3: `FromDI` marker and `@inject` decorator (HTTP resolution)

**Files:**
- Modify: `modern_di_aiohttp/main.py`, `modern_di_aiohttp/__init__.py`
- Create: `tests/test_routes.py`

Add the resolution seam: an inert `FromDI` marker inside `Annotated` hints and
an `@inject` decorator that reads the request's child container and fills
marked parameters by keyword.

- [x] **Step 1: Land the decorator**

  Commit `965d36c` — "feat: add FromDI marker and @inject decorator".

---

### Task 4: WebSocket resolution end-to-end

**Files:**
- Create: `tests/test_websockets.py`

Prove the WS path: `@inject` over a WebSocket handler resolves SESSION-scoped
providers and the connection (via the reference-only
`aiohttp_websocket_provider`), and per-message work opens a nested `REQUEST`
child of the SESSION container.

- [x] **Step 1: Land the WebSocket coverage**

  Commit `1a88973` — "test: cover websocket resolution and per-message
  request scope". 8/8 tests, 100% coverage, lint clean.

---

### Task 5: Architecture truth home + planning bundle

**Files:**
- Create: `architecture/README.md`, `architecture/container-lifecycle.md`,
  `architecture/dependency-resolution.md`, `architecture/glossary.md`
- Create: `planning/changes/2026-07-02.01-di-integration/design.md`,
  `planning/changes/2026-07-02.01-di-integration/plan.md`
- Create: `planning/releases/2.0.0.md`

Author the `architecture/` capability files (promoted from the design spec)
and the planning-convention change bundle — this is where the approved design
lands in-repo, and the initial release notes.

- [ ] **Step 1: Write the four `architecture/` files, this bundle, and the
  release notes**

  ```bash
  just check-planning
  just lint-ci
  just test-ci
  ```

  Expected: `check-planning` validates this bundle; `lint-ci` clean;
  `test-ci` still 100% (no code changed).

- [ ] **Step 2: Commit**

  ```bash
  git add architecture planning
  git commit -m "docs: add architecture truth home and planning bundle"
  ```

---

## Out of scope for this bundle

Two further tasks ship the integration but sit outside this repo/bundle:
usage docs in the `modern-di` repo (separate repo, separate PR) and creating
the GitHub repo + pushing + verifying CI (ops, no files). Both are tracked in
the full session plan, not restated here.
