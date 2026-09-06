# The child's scope follows a handshake probe, not headers and not the route

**Decision:** `_di_middleware` picks the connection kind with
`web.WebSocketResponse().can_prepare(request).ok` — aiohttp's own handshake check — and derives the
child container's scope from the provider that probe selects.

`can_prepare` is synchronous, never raises, does not consume the request and does not start the
handshake; it answers exactly the question asked, and it is aiohttp's own answer rather than a
reimplementation that can drift from it.

The alternative reviewed was dishka's header comparison, `Connection == "Upgrade"`. Rejected as
brittle: it misses the legal `keep-alive, Upgrade` form and casing variants, and it re-derives from
raw headers something the framework already computes.

Dispatching on the route was not taken either. Scope selection happens in middleware, before
routing has produced a handler, and a route table would have to be kept in sync with the handlers
by hand.

The consequence is that scope follows the request's handshake headers and nothing else: a request
that advertises a valid WebSocket upgrade opens a `SESSION` child whatever its handler actually
does, and a `REQUEST`-scoped provider would then fail to resolve for it. This is the price of
deciding before routing, and it is only reachable by a client that sends upgrade headers to a plain
HTTP endpoint.

**Revisit trigger:** a real handler needs `REQUEST` scope on a request carrying WebSocket-upgrade
headers, or aiohttp makes the connection kind available at middleware entry without a probe.
