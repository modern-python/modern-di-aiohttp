---
summary: New modern-di integration for aiohttp — per-connection middleware for scoped child containers (HTTP=REQUEST, WebSocket=SESSION) plus an @inject/FromDI decorator path.
---

# modern-di-aiohttp — integration design

**Status:** design, pending maintainer approval
**Date:** 2026-07-02
**Target:** new repo `modern-python/modern-di-aiohttp`, package `modern_di_aiohttp`

## Goal

Ship the official [modern-di](https://modern-di.modern-python.org) integration
for [aiohttp](https://docs.aiohttp.org), following the repo's
[Writing an integration](../../docs/integrations/writing-integrations.md) guide
and mirroring `modern-di-starlette` (the reference for a middleware + `@inject`
decorator hybrid: aiohttp, like Starlette, has no native request-scoped DI).

Non-goals: async resolution (resolution stays sync-only), any runtime dependency
beyond `aiohttp` and `modern-di`, shipping a separate docs site.

## Why aiohttp diverges from the Starlette reference

Two aiohttp facts drive every design decision below (verified against aiohttp
docs and the modern-di source):

1. **aiohttp is not ASGI.** A WebSocket is an ordinary HTTP GET carrying
   `Upgrade: websocket` headers; the handler upgrades it *inside* the route via
   `web.WebSocketResponse().prepare(request)`. At middleware entry the only
   connection object is `web.Request` — there is no distinct `WebSocket` type to
   `isinstance` on the way Starlette does (`Request` vs `WebSocket`).
2. **The socket lives inside one request coroutine.** The `async for msg in ws`
   loop runs in the handler; there is no framework-driven per-message scope.

### Scope decision (ruled by maintainer)

- **HTTP request → `Scope.REQUEST`**, one child container off `APP`.
- **WebSocket → `Scope.SESSION`**, one child container off `APP`. Per-message
  work opens a nested `REQUEST` child of the SESSION container (caller-driven,
  documented pattern — mirrors Dishka's `async with container() as rc:`).
- One container per connection. HTTP does **not** open a SESSION level.

Dishka precedent was reviewed: Dishka binds `Request` once at `Scope.SESSION` and
enters scopes contiguously (APP→SESSION→REQUEST for HTTP), so a single binding
serves both paths. modern-di allows scope-skipping and the maintainer wants HTTP
to be a plain REQUEST child (no SESSION), so we take the two-provider shape
instead (see below).

### WS detection

Middleware dispatches on `web.WebSocketResponse().can_prepare(request).ok`
(sync, never raises, does not consume the request or start the handshake) rather
than Dishka's brittle header equality (`Connection == "Upgrade"` misses
`keep-alive, Upgrade` and casing variants). `ok` True → `Scope.SESSION`, else
`Scope.REQUEST`.

## The connection-provider model

modern-di's `ProvidersRegistry` raises `DuplicateProviderTypeError` if two
providers bind the same type (`providers_registry.py:53`), and a
`ContextProvider` reads its value from `find_container(self.scope)` — the
ancestor at its **own** scope (`context_provider.py:49`). A REQUEST-scoped
provider is unreachable from a WS SESSION container; a SESSION-scoped provider is
unreachable from an HTTP REQUEST-off-APP container. With the connection always
typed `web.Request`, a single fixed-scope provider cannot serve both paths, and
two providers cannot both bind `web.Request` by type. Resolution:

```python
aiohttp_request_provider = providers.ContextProvider(
    scope=Scope.REQUEST, context_type=web.Request,
)
aiohttp_websocket_provider = providers.ContextProvider(
    scope=Scope.SESSION, context_type=web.Request, bound_type=None,
)
_CONNECTION_PROVIDERS = (aiohttp_request_provider, aiohttp_websocket_provider)
```

- `aiohttp_request_provider` is **registered by type** — HTTP handlers/factories
  inject the connection as bare `web.Request` (or `FromDI(aiohttp_request_provider)`).
- `aiohttp_websocket_provider` has **`bound_type=None`**, so `add_providers`
  skips it (`providers_registry.py:51`) — no `DuplicateProviderTypeError`. It
  stays fully resolvable by reference: SESSION-scoped WS factories inject the
  connection via `FromDI(aiohttp_websocket_provider)`, reachable from the SESSION
  container and every nested per-message REQUEST child.

**Documented consequence (asymmetry):** connection injection is bare-type on the
HTTP path and provider-reference on the WS path. This is inherent to aiohttp's
single-`web.Request` reality under one-container-per-connection scoping; WS
handlers also always receive `request` positionally.

## Public API (`__all__`)

Mirrors `modern-di-starlette`:

- `setup_di(app: web.Application, container: Container) -> Container`
- `fetch_di_container(app: web.Application) -> Container`
- `FromDI(dependency: AbstractProvider[T] | type[T]) -> T`  (inert `_FromDI` marker, cast to `T`)
- `inject(func) -> func`  (decorator)
- `aiohttp_request_provider`, `aiohttp_websocket_provider`

## Component design

### Storage keys
- Root container on the app: `web.AppKey("modern_di_container", Container)`
  (typed, stable since aiohttp 3.9). `fetch_di_container(app)` returns
  `app[_DI_CONTAINER_APP_KEY]`.
- Per-connection child container on the request: stashed under a module-level
  key on the request's dict interface (`request[_CONTAINER_KEY] = child`), read
  back by `inject`. (Plain aiohttp `RequestKey`/string key — `request` is a
  `MutableMapping`, same idea as Starlette stashing on the ASGI scope dict.)

### `setup_di(app, container)`
1. `app[_DI_CONTAINER_APP_KEY] = container`
2. `container.providers_registry.add_providers(*_CONNECTION_PROVIDERS)`
3. `app.on_startup.append(_on_startup)` where `_on_startup` calls
   `container.open()` (reopen-on-restart so a second run doesn't raise
   `ContainerClosedError`).
4. `app.on_cleanup.append(_on_cleanup)` where `_on_cleanup` awaits
   `container.close_async()`.
5. `app.middlewares.append(_di_middleware)`
6. return container

Startup/cleanup callbacks are `async def cb(app: web.Application) -> None`. The
container is read back from `app` inside them (not captured) so a copied/reused
app stays consistent.

### `_di_middleware` (`@web.middleware`)
```python
@web.middleware
async def _di_middleware(request, handler):
    scope = Scope.SESSION if web.WebSocketResponse().can_prepare(request).ok else Scope.REQUEST
    child = fetch_di_container(request.app).build_child_container(
        context={web.Request: request}, scope=scope,
    )
    request[_CONTAINER_KEY] = child
    try:
        return await handler(request)
    finally:
        await child.close_async()
```

### `FromDI` + `inject`
Same shape as `modern-di-starlette`: inert frozen slotted `_FromDI(dependency)`
dataclass; `FromDI` returns it cast to `T`. `inject` parses the handler's
`Annotated` hints once at decoration time for `_FromDI` markers, then at call
time reads `request[_CONTAINER_KEY]` (raising a clear `RuntimeError` if absent,
pointing at `setup_di`) and resolves each marked param — `resolve_provider` for
an `AbstractProvider`, `resolve` for a bare type — passing them by keyword into
the wrapped handler. Handler signature stays `async def handler(request, ...)`;
DI params are keyword-filled, not stripped (aiohttp parses no CLI args, unlike
Typer, so no signature rewrite needed — same as Starlette).

## Lifecycle rules applied
- Root reopens on startup (`container.open()` via `on_startup`).
- Root closes on cleanup (`close_async` via `on_cleanup`).
- Child always closed in `finally` (`close_async`).
- Async throughout (`close_async`), matching aiohttp.

## Tests (100% coverage gate, mirrors modern-di-starlette)
- `dependencies.py` — sample `Group`: APP `Factory`, SESSION factory, REQUEST
  factory, a REQUEST factory reading `web.Request` by bare type (proves HTTP
  context injection), and a SESSION factory reading the connection via
  `aiohttp_websocket_provider` (proves WS context injection).
- `conftest.py` — build a `web.Application`, `setup_di(app, Container(groups=[Dependencies]))`,
  yield an `aiohttp` test client (`aiohttp.test_utils.TestClient` / `pytest-aiohttp`).
- `test_lifespan.py` — startup/cleanup opens+closes the root; restart (second run)
  does not raise `ContainerClosedError`.
- `test_routes.py` — HTTP resolution through `FromDI` (provider ref + bare type);
  REQUEST/APP scoping; bare `web.Request` injection into a REQUEST factory.
- `test_middleware.py` — child built at the dispatched scope and closed after;
  `@inject` without `setup_di` raises the clear `RuntimeError`.
- `test_websockets.py` — `can_prepare` dispatch → SESSION; WS resolution via
  `FromDI(aiohttp_websocket_provider)`; the per-message nested-REQUEST pattern;
  connection read from `aiohttp_websocket_provider`.

## Repo scaffolding (mirror modern-di-starlette)
- Layout: `modern_di_aiohttp/main.py` (whole implementation), re-exporting
  `__init__.py` with explicit `__all__`, `py.typed`.
- `pyproject.toml`: `name = "modern-di-aiohttp"`,
  `description = "modern-di integration for aiohttp"`, deps
  `["aiohttp>=3.9,<4", "modern-di>=2.21.0,<3"]`, `version = "0"`, Python
  3.10–3.14 classifiers, `[project.urls]` → shared docs + own repo, keywords incl.
  `aiohttp`. Dev group adds `pytest-aiohttp` (test client) in place of `httpx2`.
- Mirror `Justfile`, `CLAUDE.md`, `.github/workflows/` (CI, release via PyPI
  Trusted Publishing, scheduled), `.gitignore`, `LICENSE` (MIT), `README.md`.
- `architecture/`: `README.md`, `container-lifecycle.md`
  (`setup_di` + signals + the per-connection middleware child),
  `dependency-resolution.md` (`FromDI` + `@inject`), `glossary.md`.
- `planning/` — planning-convention bundle mirrored from starlette; this design
  becomes `planning/changes/2026-07-02.01-di-integration/design.md` with a
  matching `plan.md`; `2.0.0.md` release notes.

## Docs in the `modern-di` repo (separate PR-able change, same as other integrations)
- Add `docs/integrations/aiohttp.md` (usage: install, `setup_di`, `@inject` +
  `FromDI` example, scopes note, the WS per-message nested-REQUEST pattern).
- Add nav entry in `mkdocs.yml` under `Integrations` (after Typer / before
  Pytest, or alphabetical — match existing order).

## Release
Tag-driven, mirroring the others: write `planning/releases/2.0.0.md`, push a bare
semver tag off green `main`; `just publish` sets the version from the tag.

## Repo creation mechanics
- Create `../modern-di-aiohttp` working dir.
- `gh repo create modern-python/modern-di-aiohttp` (private/public to match the
  org's other integration repos), push `main`, watch CI.
