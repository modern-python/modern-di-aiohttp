import collections.abc
import http
import typing

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, make_mocked_request

from modern_di_aiohttp import FromDI, inject
from tests.dependencies import Dependencies, DependentCreator, SimpleCreator


AiohttpClient = collections.abc.Callable[[web.Application], collections.abc.Awaitable[TestClient]]


async def test_factories_by_type_and_provider(aiohttp_client: AiohttpClient, app: web.Application) -> None:
    @inject
    async def read_root(
        request: web.Request,  # noqa: ARG001
        app_factory_instance: typing.Annotated[SimpleCreator, FromDI(SimpleCreator)],
        request_factory_instance: typing.Annotated[DependentCreator, FromDI(Dependencies.request_factory)],
    ) -> web.Response:
        assert isinstance(app_factory_instance, SimpleCreator)
        assert isinstance(request_factory_instance, DependentCreator)
        assert request_factory_instance.dep1 is not app_factory_instance
        return web.Response(text="ok")

    app.router.add_get("/", read_root)
    client = await aiohttp_client(app)
    response = await client.get("/")
    assert response.status == http.HTTPStatus.OK
    assert await response.text() == "ok"


async def test_context_provider_reads_request(aiohttp_client: AiohttpClient, app: web.Application) -> None:
    @inject
    async def read_root(
        request: web.Request,  # noqa: ARG001
        method: typing.Annotated[str, FromDI(Dependencies.request_method)],
    ) -> web.Response:
        assert method == "GET"
        return web.Response(text=method)

    app.router.add_get("/", read_root)
    client = await aiohttp_client(app)
    response = await client.get("/")
    assert await response.text() == "GET"


async def test_inject_without_setup_di_raises_clear_error() -> None:
    @inject
    async def read_root(
        request: web.Request,  # noqa: ARG001
        app_factory_instance: typing.Annotated[SimpleCreator, FromDI(SimpleCreator)],
    ) -> web.Response:
        return web.Response(text=app_factory_instance.dep1)  # pragma: no cover -- RuntimeError precedes this

    request = make_mocked_request("GET", "/")
    with pytest.raises(RuntimeError, match="setup_di"):
        await read_root(request)
