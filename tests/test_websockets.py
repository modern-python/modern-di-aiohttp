import collections.abc
import typing

from aiohttp import web
from aiohttp.test_utils import TestClient
from modern_di import Container, Scope

from modern_di_aiohttp import FromDI, aiohttp_websocket_provider, inject
from modern_di_aiohttp.main import _CONTAINER_REQUEST_KEY
from tests.dependencies import Dependencies, DependentCreator, SimpleCreator


AiohttpClient = collections.abc.Callable[[web.Application], collections.abc.Awaitable[TestClient]]


async def test_websocket_resolves_session_scope_and_per_message_request(
    aiohttp_client: AiohttpClient, app: web.Application
) -> None:
    @inject
    async def ws_handler(
        request: web.Request,
        app_factory_instance: typing.Annotated[SimpleCreator, FromDI(SimpleCreator)],
        session_factory_instance: typing.Annotated[DependentCreator, FromDI(Dependencies.session_factory)],
        connection: typing.Annotated[web.Request, FromDI(aiohttp_websocket_provider)],
    ) -> web.WebSocketResponse:
        assert isinstance(app_factory_instance, SimpleCreator)
        assert isinstance(session_factory_instance, DependentCreator)
        assert connection is request  # aiohttp reuses the request object as the connection
        session_container: Container = request[_CONTAINER_REQUEST_KEY]
        assert session_container.scope is Scope.SESSION

        ws = web.WebSocketResponse()
        await ws.prepare(request)
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                # per-message nested REQUEST scope, a child of the SESSION container
                async with session_container.build_child_container(scope=Scope.REQUEST) as request_container:
                    per_message = request_container.resolve_provider(Dependencies.request_factory)
                    assert isinstance(per_message, DependentCreator)
                await ws.send_str("pong")
                await ws.close()
        return ws

    app.router.add_get("/ws", ws_handler)
    client = await aiohttp_client(app)
    async with client.ws_connect("/ws") as ws:
        await ws.send_str("ping")
        assert (await ws.receive()).data == "pong"
