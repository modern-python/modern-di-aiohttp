import collections.abc
import http

from aiohttp import web
from aiohttp.test_utils import TestClient
from modern_di import Container, Scope

from modern_di_aiohttp.main import _CONTAINER_REQUEST_KEY, fetch_request_container
from tests.dependencies import Dependencies, DependentCreator


AiohttpClient = collections.abc.Callable[[web.Application], collections.abc.Awaitable[TestClient]]


async def test_middleware_opens_request_scoped_child(aiohttp_client: AiohttpClient, app: web.Application) -> None:
    async def endpoint(request: web.Request) -> web.Response:
        child = request[_CONTAINER_REQUEST_KEY]
        assert isinstance(child, Container)
        assert child.scope is Scope.REQUEST
        assert isinstance(child.resolve_provider(Dependencies.request_factory), DependentCreator)
        return web.Response(text="ok")

    app.router.add_get("/", endpoint)
    client = await aiohttp_client(app)
    assert (await client.get("/")).status == http.HTTPStatus.OK


async def test_middleware_opens_session_scoped_child_for_websocket(
    aiohttp_client: AiohttpClient, app: web.Application
) -> None:
    async def ws_endpoint(request: web.Request) -> web.WebSocketResponse:
        child = request[_CONTAINER_REQUEST_KEY]
        assert isinstance(child, Container)
        assert child.scope is Scope.SESSION
        assert isinstance(child.resolve_provider(Dependencies.session_factory), DependentCreator)
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await ws.send_str("ok")
        await ws.close()
        return ws

    app.router.add_get("/ws", ws_endpoint)
    client = await aiohttp_client(app)
    async with client.ws_connect("/ws") as ws:
        assert (await ws.receive()).data == "ok"


async def test_child_container_closed_after_request(aiohttp_client: AiohttpClient, app: web.Application) -> None:
    captured: list[Container] = []

    async def endpoint(request: web.Request) -> web.Response:
        captured.append(fetch_request_container(request))
        return web.Response(text="ok")

    app.router.add_get("/", endpoint)
    client = await aiohttp_client(app)
    assert (await client.get("/")).status == http.HTTPStatus.OK
    assert captured[0].closed is True


async def test_child_container_closed_when_handler_raises(aiohttp_client: AiohttpClient, app: web.Application) -> None:
    captured: list[Container] = []

    async def endpoint(request: web.Request) -> web.Response:
        captured.append(fetch_request_container(request))
        raise web.HTTPInternalServerError

    app.router.add_get("/", endpoint)
    client = await aiohttp_client(app)
    assert (await client.get("/")).status == http.HTTPStatus.INTERNAL_SERVER_ERROR
    assert captured[0].closed is True
