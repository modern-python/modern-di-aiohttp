import collections.abc
import http
import typing

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient

from modern_di_aiohttp import FromDI, aiohttp_websocket_provider, inject
from tests.dependencies import Dependencies, DependentCreator, SimpleCreator


AiohttpClient = collections.abc.Callable[[web.Application], collections.abc.Awaitable[TestClient]]


async def test_view_method_resolves_markers(aiohttp_client: AiohttpClient, app: web.Application) -> None:
    class View(web.View):
        @inject
        async def get(
            self,
            app_factory_instance: typing.Annotated[SimpleCreator, FromDI(SimpleCreator)],
            request_factory_instance: typing.Annotated[DependentCreator, FromDI(Dependencies.request_factory)],
            method: typing.Annotated[str, FromDI(Dependencies.request_method)],
        ) -> web.Response:
            assert isinstance(self, View)
            assert isinstance(app_factory_instance, SimpleCreator)
            assert isinstance(request_factory_instance, DependentCreator)
            assert request_factory_instance.dep1 is not app_factory_instance
            return web.Response(text=method)

    app.router.add_view("/", View)
    client = await aiohttp_client(app)
    response = await client.get("/")
    assert response.status == http.HTTPStatus.OK
    assert await response.text() == "GET"


async def test_view_websocket_resolves_session_scope(aiohttp_client: AiohttpClient, app: web.Application) -> None:
    class View(web.View):
        @inject
        async def get(
            self,
            session_factory_instance: typing.Annotated[DependentCreator, FromDI(Dependencies.session_factory)],
            connection: typing.Annotated[web.Request, FromDI(aiohttp_websocket_provider)],
        ) -> web.WebSocketResponse:
            assert isinstance(session_factory_instance, DependentCreator)
            assert connection is self.request
            ws = web.WebSocketResponse()
            await ws.prepare(self.request)
            await ws.send_str("hello")
            await ws.close()
            return ws

    app.router.add_view("/ws", View)
    client = await aiohttp_client(app)
    async with client.ws_connect("/ws") as ws:
        assert await ws.receive_str() == "hello"


async def test_inject_without_request_argument_raises_clear_error() -> None:
    @inject
    async def handler(
        value: str,
        app_factory_instance: typing.Annotated[SimpleCreator, FromDI(SimpleCreator)],
    ) -> str:
        return f"{value}:{app_factory_instance.dep1}"  # pragma: no cover -- TypeError precedes this

    with pytest.raises(TypeError, match=r"web\.Request or a web\.View"):
        await handler("value")
