"""modern-di integration for aiohttp."""

import dataclasses
import functools
import typing

from aiohttp import web
from modern_di import Container, Scope, integrations, providers


T_co = typing.TypeVar("T_co", covariant=True)
T = typing.TypeVar("T")


# aiohttp exposes only `web.Request` at middleware entry (a WebSocket is an
# upgraded HTTP request), so both connection providers bind `web.Request`. The
# providers registry rejects two providers of the same type, so the websocket
# provider is reference-only (`bound_type=None`): not registered by type, but
# resolvable via `FromDI(aiohttp_websocket_provider)` from the SESSION container.
aiohttp_request_provider = providers.ContextProvider(scope=Scope.REQUEST, context_type=web.Request)
aiohttp_websocket_provider = providers.ContextProvider(scope=Scope.SESSION, context_type=web.Request, bound_type=None)
_CONNECTION_PROVIDERS = (aiohttp_request_provider, aiohttp_websocket_provider)

# Root container on the aiohttp application (typed key, aiohttp >= 3.9).
_DI_CONTAINER_APP_KEY: "web.AppKey[Container]" = web.AppKey("modern_di_container", Container)
# Per-connection child container, stashed on the request's dict interface.
_CONTAINER_REQUEST_KEY = "modern_di_child_container"


def fetch_di_container(app: web.Application) -> Container:
    return app[_DI_CONTAINER_APP_KEY]


def fetch_request_container(request: web.Request) -> Container:
    """Return the per-connection child container the middleware built for this request."""
    try:
        return request[_CONTAINER_REQUEST_KEY]
    except KeyError:
        msg = (
            "No modern-di container found on the request. "
            "Call setup_di(app, container) so requests pass through the modern-di middleware "
            "before using @inject or fetch_request_container."
        )
        raise RuntimeError(msg) from None


async def _on_startup(app: web.Application) -> None:
    # Reopen so a second run of the same container (reload, test re-entry) does
    # not raise ContainerClosedError; reopening an open container is a no-op.
    fetch_di_container(app).open()


async def _on_cleanup(app: web.Application) -> None:
    await fetch_di_container(app).close_async()


@web.middleware
async def _di_middleware(
    request: web.Request,
    handler: typing.Callable[[web.Request], typing.Awaitable[web.StreamResponse]],
) -> web.StreamResponse:
    # `can_prepare` never raises and does not start the handshake; it only checks
    # whether the request is a valid WebSocket upgrade. Both connection providers
    # bind `web.Request`, so `integrations.classify_connection`'s isinstance
    # dispatch can't tell them apart — this probe is what picks the provider;
    # `integrations.bind` only derives the scope+context once it's picked.
    provider = (
        aiohttp_websocket_provider if web.WebSocketResponse().can_prepare(request).ok else aiohttp_request_provider
    )
    match = integrations.bind(provider, request)
    async with fetch_di_container(request.app).build_child_container(
        scope=match.scope, context=match.context
    ) as child_container:
        request[_CONTAINER_REQUEST_KEY] = child_container
        return await handler(request)


def setup_di(app: web.Application, container: Container) -> Container:
    app[_DI_CONTAINER_APP_KEY] = container
    container.add_providers(*_CONNECTION_PROVIDERS)
    app.on_startup.append(_on_startup)
    app.on_cleanup.append(_on_cleanup)
    app.middlewares.append(_di_middleware)
    return container


@dataclasses.dataclass(slots=True, frozen=True)
class _FromDI(typing.Generic[T_co]):
    dependency: providers.AbstractProvider[T_co] | type[T_co]


def FromDI(dependency: providers.AbstractProvider[T_co] | type[T_co]) -> T_co:  # noqa: N802
    return typing.cast(T_co, _FromDI(dependency))


def _parse_inject_params(func: typing.Callable[..., typing.Any]) -> dict[str, _FromDI[typing.Any]]:
    hints = typing.get_type_hints(func, include_extras=True)
    di_params: dict[str, _FromDI[typing.Any]] = {}
    for name, hint in hints.items():
        if name == "return":
            continue
        if typing.get_origin(hint) is typing.Annotated:
            for meta in typing.get_args(hint)[1:]:
                if isinstance(meta, _FromDI):
                    di_params[name] = meta
                    break
    return di_params


def _resolve_di_params(container: Container, di_params: dict[str, _FromDI[typing.Any]]) -> dict[str, typing.Any]:
    return {name: container.resolve_dependency(marker.dependency) for name, marker in di_params.items()}


def inject(func: typing.Callable[..., typing.Awaitable[T]]) -> typing.Callable[..., typing.Awaitable[T]]:
    di_params = _parse_inject_params(func)

    @functools.wraps(func)
    async def wrapper(request: web.Request) -> T:
        child_container = fetch_request_container(request)
        return await func(request, **_resolve_di_params(child_container, di_params))

    return wrapper
