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
   (checks the handshake without starting it or raising).
2. Opens a `Scope.SESSION` child for a WebSocket, else a `Scope.REQUEST` child,
   with `{web.Request: request}` injected as context.
3. Stashes the child on the request under `_CONTAINER_REQUEST_KEY`.
4. `close_async`s the child when the handler returns (for a WebSocket that is
   when the socket closes, since the handler owns the socket's whole lifetime).

Per-message work inside a WebSocket handler opens a nested `Scope.REQUEST` child
of the SESSION container (`session_container.build_child_container(scope=Scope.REQUEST)`).
