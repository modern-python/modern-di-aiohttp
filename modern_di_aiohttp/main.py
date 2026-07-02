"""modern-di integration for aiohttp."""

import enum
import typing

from aiohttp import web
from modern_di import Container, Scope, providers


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
_CONTAINER_REQUEST_KEY = "modern_di_container"


def fetch_di_container(app: web.Application) -> Container:
    return app[_DI_CONTAINER_APP_KEY]


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
    # whether the request is a valid WebSocket upgrade.
    connection_scope: enum.IntEnum = Scope.SESSION if web.WebSocketResponse().can_prepare(request).ok else Scope.REQUEST
    child_container = fetch_di_container(request.app).build_child_container(
        context={web.Request: request}, scope=connection_scope
    )
    request[_CONTAINER_REQUEST_KEY] = child_container
    try:
        return await handler(request)
    finally:
        await child_container.close_async()


def setup_di(app: web.Application, container: Container) -> Container:
    app[_DI_CONTAINER_APP_KEY] = container
    container.providers_registry.add_providers(*_CONNECTION_PROVIDERS)
    app.on_startup.append(_on_startup)
    app.on_cleanup.append(_on_cleanup)
    app.middlewares.append(_di_middleware)
    return container
