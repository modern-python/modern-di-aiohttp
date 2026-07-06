import collections.abc
import http

import modern_di
from aiohttp import web
from aiohttp.test_utils import TestClient

from modern_di_aiohttp import fetch_di_container, setup_di
from modern_di_aiohttp.main import _on_cleanup, _on_startup
from tests.dependencies import Dependencies


AiohttpClient = collections.abc.Callable[[web.Application], collections.abc.Awaitable[TestClient]]


async def _ok(request: web.Request) -> web.Response:  # noqa: ARG001
    return web.Response(text="ok")


async def test_startup_reopens_closed_root(aiohttp_client: AiohttpClient) -> None:
    container = modern_di.Container(groups=[Dependencies], validate=True)
    container.close_sync()
    assert container.closed

    app = web.Application()
    setup_di(app, container)
    app.router.add_get("/", _ok)

    client = await aiohttp_client(app)
    response = await client.get("/")
    # reopened on startup; a closed root would raise ContainerClosedError
    assert response.status == http.HTTPStatus.OK


async def test_cleanup_closes_root() -> None:
    app = web.Application()
    container = modern_di.Container(groups=[Dependencies], validate=True)
    setup_di(app, container)

    await _on_startup(app)
    assert not container.closed
    await _on_cleanup(app)
    assert container.closed
    assert fetch_di_container(app) is container
