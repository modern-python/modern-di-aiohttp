# Two connection providers, one registered by type and one reference-only

**Decision:** the connection is exposed by two `ContextProvider`s — `aiohttp_request_provider` at
`Scope.REQUEST`, registered by type, and `aiohttp_websocket_provider` at `Scope.SESSION` with
`bound_type=None` — rather than by a single provider serving both connection kinds.

Two facts fix the shape. aiohttp is not ASGI: a WebSocket is an ordinary HTTP GET carrying
`Upgrade` headers, upgraded *inside* the route handler, so the only connection object at middleware
entry is a `web.Request` for both kinds — there is no second type to bind. And a `ContextProvider`
reads its value from the ancestor at its **own** scope, so a `REQUEST`-scoped provider is
unreachable from a WebSocket's `SESSION` container and a `SESSION`-scoped one is unreachable from
an HTTP `REQUEST`-off-`APP` container. One fixed-scope provider cannot serve both paths, and
modern-di's providers registry admits one provider per bound type, so two cannot both be registered
by type.

The alternative is dishka's: bind the connection once at `Scope.SESSION` and enter scopes
contiguously, `APP → SESSION → REQUEST` for HTTP as well, so a single binding serves both paths.
Rejected because modern-di permits scope-skipping and the shape we want is one container per
connection, with HTTP a plain `REQUEST` child of `APP` and no `SESSION` level opened for it.
Contiguous scopes would buy the single binding by giving every HTTP request a container it has no
use for.

Making the WebSocket provider reference-only is what buys the second provider: `add_providers`
skips a provider with no bound type, so no `DuplicateProviderTypeError`, while the provider stays
fully resolvable by reference from the `SESSION` container and every nested per-message `REQUEST`
child.

The consequence is an asymmetry that is documented rather than hidden: on the HTTP path the
connection is injected as a bare `web.Request`, on the WebSocket path only as
`FromDI(aiohttp_websocket_provider)`. That asymmetry is inherent to aiohttp's single-`web.Request`
reality under one-container-per-connection scoping, not a rough edge to file off; WebSocket
handlers also always receive `request` positionally, so the loss is small.

**Revisit trigger:** aiohttp exposes a distinct connection object for WebSockets at middleware
entry, or modern-di admits two providers under one bound type. Either removes the constraint the
two-provider split exists to satisfy, and the connection should then be a single provider bound by
type on both paths.
