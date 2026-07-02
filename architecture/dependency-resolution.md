# Dependency resolution

aiohttp has no dependency-injection system of its own, so `modern-di-aiohttp`
uses an inert marker plus a decorator (the decorator path from modern-di's
"Writing an integration" guide).

## FromDI

`FromDI(dependency)` marks a handler parameter for injection inside an
`Annotated` hint:

    service: typing.Annotated[Service, FromDI(Deps.service)]

It returns `typing.cast(T, _FromDI(dependency))`: type checkers see the resolved
type `T`, while at runtime it is a frozen `_FromDI` marker the decorator detects.
The argument is a provider (`AbstractProvider`) or a bare type — resolution
handles both (`resolve_provider` vs `resolve`).

## @inject

`inject` wraps a handler. At decoration time it reads
`typing.get_type_hints(func, include_extras=True)` and collects the parameters
whose `Annotated` metadata holds a `_FromDI`. aiohttp calls a handler with just
the request (`handler(request)`) and does not introspect its signature, so — unlike
a CLI integration — no signature rewrite is needed.

At call time the wrapper:

1. Reads the per-connection child container from `request[_CONTAINER_REQUEST_KEY]`
   (put there by `_di_middleware`); a missing key raises a `RuntimeError` pointing
   at `setup_di`.
2. Resolves each marked parameter.
3. Calls the handler with the request plus the resolved parameters by keyword.

The `web.Request` a provider receives as DI context is the same object aiohttp
passes to the handler.
