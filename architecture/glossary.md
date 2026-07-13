# Glossary

The ubiquitous language of `modern-di-aiohttp`.

**Root container**:
The application-lifetime `modern_di.Container` passed to `setup_di` and stored on
the app under `web.AppKey("modern_di_container", Container)`; opened on startup and
closed on cleanup.
_Avoid_: app container (in prose), global container.

**Child container**:
The per-connection container built by the middleware — `Scope.REQUEST` for an HTTP
request, `Scope.SESSION` for a WebSocket — and closed when the connection ends.
_Avoid_: request container (ambiguous across scopes), sub-container.

**Connection provider**:
A `ContextProvider` exposing the connection `web.Request`: `aiohttp_request_provider`
(REQUEST, by type) and the reference-only `aiohttp_websocket_provider` (SESSION).

**FromDI marker**:
The inert `Annotated` metadata (`modern_di.integrations.Marker`) that flags a
handler parameter for resolution by `@inject`.
_Avoid_: Depends (that is FastAPI's mechanism).
