# Two connection providers, one registered by type and one reference-only

aiohttp is not ASGI: a WebSocket is an ordinary HTTP GET upgraded inside the route handler, so the
only connection object at middleware entry is a `web.Request` for both kinds. A `ContextProvider`
reads its value from the ancestor at its own scope, so one fixed-scope provider cannot serve both
the HTTP `REQUEST` child and the WebSocket `SESSION` child, and modern-di's registry admits one
provider per bound type. The connection is therefore two providers: `aiohttp_request_provider` at
`Scope.REQUEST` bound by type, and `aiohttp_websocket_provider` at `Scope.SESSION` with
`bound_type=None`, which `add_providers` skips rather than rejecting as a duplicate while leaving
it resolvable by reference. dishka's alternative, binding once at `SESSION` and entering
`APP -> SESSION -> REQUEST` for HTTP too, was rejected because it gives every HTTP request a
container it has no use for. The cost is an asymmetry: HTTP handlers inject a bare `web.Request`,
WebSocket handlers use `FromDI(aiohttp_websocket_provider)`.
