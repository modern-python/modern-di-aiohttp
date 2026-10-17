import collections.abc
import http
import inspect
import typing

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, make_mocked_request

from modern_di_aiohttp import FromDI, inject
from tests.dependencies import Dependencies, DependentCreator, SimpleCreator


AiohttpClient = collections.abc.Callable[[web.Application], collections.abc.Awaitable[TestClient]]


async def test_sync_handler_resolves_markers(aiohttp_client: AiohttpClient, app: web.Application) -> None:
    @inject
    def read_root(
        request: web.Request,  # noqa: ARG001
        app_factory_instance: typing.Annotated[SimpleCreator, FromDI(SimpleCreator)],
        request_factory_instance: typing.Annotated[DependentCreator, FromDI(Dependencies.request_factory)],
        method: typing.Annotated[str, FromDI(Dependencies.request_method)],
    ) -> web.Response:
        assert isinstance(request_factory_instance, DependentCreator)
        return web.Response(text=f"{method}:{app_factory_instance.dep1}")

    with pytest.warns(DeprecationWarning, match="Bare functions"):
        app.router.add_get("/", read_root)  # ty: ignore[invalid-argument-type]
    client = await aiohttp_client(app)
    response = await client.get("/")
    assert response.status == http.HTTPStatus.OK
    assert await response.text() == "GET:original"


def test_inject_keeps_sync_and_async_kinds() -> None:
    def sync_handler(request: web.Request) -> None: ...

    async def async_handler(request: web.Request) -> None: ...

    assert not inspect.iscoroutinefunction(inject(sync_handler))
    assert inspect.iscoroutinefunction(inject(async_handler))


def test_sync_inject_without_request_argument_raises_clear_error() -> None:
    @inject
    def handler(
        value: str,
        app_factory_instance: typing.Annotated[SimpleCreator, FromDI(SimpleCreator)],
    ) -> str:
        return f"{value}:{app_factory_instance.dep1}"  # pragma: no cover -- TypeError precedes this call

    with pytest.raises(TypeError, match=r"web\.Request or a web\.View"):
        handler("value")


def test_sync_inject_without_setup_di_raises_clear_error() -> None:
    @inject
    def read_root(
        request: web.Request,  # noqa: ARG001
        app_factory_instance: typing.Annotated[SimpleCreator, FromDI(SimpleCreator)],
    ) -> web.Response:
        return web.Response(text=app_factory_instance.dep1)  # pragma: no cover -- RuntimeError precedes this call

    with pytest.raises(RuntimeError, match="setup_di"):
        read_root(make_mocked_request("GET", "/"))
