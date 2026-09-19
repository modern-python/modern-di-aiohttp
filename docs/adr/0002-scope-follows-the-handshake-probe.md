# The child's scope follows a handshake probe, not headers and not the route

Both connection providers bind `web.Request`
(see [ADR-0001](0001-two-connection-providers-one-reference-only.md)), so
`integrations.classify_connection`'s isinstance dispatch cannot tell them apart and
`_di_middleware` picks the kind itself with `web.WebSocketResponse().can_prepare(request).ok`,
passing the chosen provider to `integrations.bind` for the child's scope and context. The probe is
aiohttp's own handshake check rather than a reimplementation that can drift from it: on a fresh
response object it cannot raise, it is synchronous, and it neither consumes the request nor starts
the handshake. dishka's `Connection == "Upgrade"` header comparison was rejected as brittle, missing
the legal `keep-alive, Upgrade` form and casing variants, and dispatching on the route was
unavailable because scope selection runs before routing has produced a handler. The boundary is that
scope follows the handshake headers and nothing else, so a request advertising a valid upgrade to a
plain HTTP endpoint opens a `SESSION` child and a `REQUEST`-scoped provider then fails to resolve.
