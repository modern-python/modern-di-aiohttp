# Container lifecycle

`modern-di-aiohttp` wires a `modern_di.Container` into an aiohttp
`web.Application`, opens and closes it around the app's startup/cleanup signals,
and builds a scoped child container per connection.

## setup_di

`setup_di(app, container)` does five things and returns the container:

1. Stashes the root container on the app under `web.AppKey("modern_di_container",
   Container)` (read back with `fetch_di_container(app)`).
2. Registers the connection providers (`aiohttp_request_provider`) on the
   container's providers registry. `aiohttp_websocket_provider` is reference-only
   (`bound_type=None`) and is skipped by registration.
3. Appends `_on_startup` to `app.on_startup` — it reopens the root container so a
   second run (reload, test re-entry) does not raise `ContainerClosedError`.
4. Appends `_on_cleanup` to `app.on_cleanup` — it `close_async`s the root.
5. Appends `_di_middleware` to `app.middlewares`.

Call it once, after creating the app and before it starts serving.

## Connection providers

aiohttp exposes only `web.Request` at middleware entry — a WebSocket is an
upgraded HTTP GET, not a distinct connection type. Both connection providers
therefore bind `web.Request`, and the providers registry forbids two providers of
one type, so:

- `aiohttp_request_provider` — `Scope.REQUEST`, registered by type. HTTP handlers
  and REQUEST-scoped factories read the connection as bare `web.Request`.
- `aiohttp_websocket_provider` — `Scope.SESSION`, `bound_type=None` (reference-
  only). WebSocket handlers read the connection via
  `FromDI(aiohttp_websocket_provider)`.

## Per-connection child container

`_di_middleware` (`@web.middleware`) runs for every request. It:

1. Detects a WebSocket upgrade with `web.WebSocketResponse().can_prepare(request).ok`
   (checks the handshake without starting it or raising) and picks
   `aiohttp_websocket_provider` or `aiohttp_request_provider` accordingly — this
   probe is aiohttp's own; `modern_di.integrations.classify_connection`'s
   isinstance-over-tuple dispatch can't do it, since both providers bind
   `web.Request`.
2. Derives the child's scope and context from the picked provider via
   `modern_di.integrations.bind(provider, request)` — `Scope.SESSION` for a
   WebSocket, else `Scope.REQUEST`, with `{web.Request: request}` injected as
   context.
3. Opens the child as an `async with` block — `Container.build_child_container`
   returns a container that is already open, so entering it is a no-op — and
   stashes it on the request under `_CONTAINER_REQUEST_KEY` for the duration of
   the block.
4. Exiting the block closes the child (`close_async`), including on the
   exception path — for a WebSocket that is when the socket closes, since the
   handler owns the socket's whole lifetime.

Per-message work inside a WebSocket handler opens a nested `Scope.REQUEST` child
of the SESSION container (`session_container.build_child_container(scope=Scope.REQUEST)`).

Scope selection is derived from the request's handshake headers via `can_prepare`,
not from the route, so a request carrying valid WebSocket-upgrade headers opens a
SESSION child regardless of what its handler actually does — a REQUEST-scoped
provider would then fail to resolve for such a request.
