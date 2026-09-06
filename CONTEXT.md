# modern-di-aiohttp

The [`modern-di`](https://github.com/modern-python/modern-di) integration for
[aiohttp](https://docs.aiohttp.org): `setup_di` binds a container to a `web.Application`, middleware
opens one scoped child container per connection, and an `@inject` decorator resolves the
`FromDI`-marked parameters of a handler from it.

## Language

A term is listed only when there is a synonym to reject, or a meaning subtle enough that code and
docs must agree on it. General programming vocabulary does not belong here, however heavily this
package uses it.

The domain terms are `modern-di`'s — `Container`, `Provider`, `Group`, `Scope`, `Resolution`,
`Override`. That project's `CONTEXT.md` is the authority for all of them; nothing here redefines
one. The three below are this package's own, and all three exist to say *which* container or
connection is meant, because this package always has more than one of each in play.

**Root container**:
The application-lifetime `Container` handed to `setup_di` and stored on the `web.Application`,
opened on startup and closed on cleanup. Every other container here descends from it, so an
unqualified "the container" is ambiguous in this repo and should not be written.

**Child container**:
The container the middleware opens for one connection and closes when that connection ends —
`Scope.REQUEST` for an HTTP request, `Scope.SESSION` for a WebSocket. Per-message work inside a
WebSocket handler opens a further `Scope.REQUEST` child of the session one; that is a child
container too.
_Avoid_: request container. `fetch_request_container()` returns this, and on a WebSocket what it
returns is `SESSION`-scoped — reading the function's name as the term names the wrong scope.

**Connection provider**:
A `ContextProvider` exposing the connection object itself. `modern-di` calls that object the
Connection and rejects "request" for it as too HTTP-specific; in aiohttp it is a `web.Request`
either way, since a WebSocket is an upgraded HTTP GET and not a distinct type. Hence two of them,
`aiohttp_request_provider` and `aiohttp_websocket_provider`, one per connection kind rather than
one per bound type.
