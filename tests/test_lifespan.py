import collections.abc
import dataclasses
import http
import typing

import modern_di
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from modern_di import providers

from modern_di_aiohttp import FromDI, fetch_di_container, inject, setup_di
from modern_di_aiohttp.main import _on_cleanup, _on_startup
from tests.dependencies import Dependencies


AiohttpClient = collections.abc.Callable[[web.Application], collections.abc.Awaitable[TestClient]]


async def _ok(request: web.Request) -> web.Response:  # noqa: ARG001
    return web.Response(text="ok")


async def test_startup_reopens_closed_root(aiohttp_client: AiohttpClient) -> None:
    container = modern_di.Container(groups=[Dependencies])
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
    container = modern_di.Container(groups=[Dependencies])
    setup_di(app, container)

    await _on_startup(app)
    assert not container.closed
    await _on_cleanup(app)
    assert container.closed
    assert fetch_di_container(app) is container


@dataclasses.dataclass(kw_only=True, slots=True)
class Label:
    name: str


def build_unmanaged_app(finalized: list[str]) -> tuple[web.Application, modern_di.Container]:
    class LabelDependencies(modern_di.Group):
        app_label = providers.Factory(
            creator=lambda: Label(name="app"),
            bound_type=None,
            cache=providers.CacheSettings(finalizer=lambda label: finalized.append(label.name)),
        )
        request_label = providers.Factory(
            scope=modern_di.Scope.REQUEST,
            creator=lambda: Label(name="request"),
            bound_type=None,
            cache=providers.CacheSettings(finalizer=lambda label: finalized.append(label.name)),
        )

    @inject
    async def labels(
        request: web.Request,  # noqa: ARG001
        app_label: typing.Annotated[Label, FromDI(LabelDependencies.app_label)],
        request_label: typing.Annotated[Label, FromDI(LabelDependencies.request_label)],
    ) -> web.Response:
        return web.Response(text=f"{app_label.name},{request_label.name}")

    app = web.Application()
    container = modern_di.Container(groups=[LabelDependencies])
    setup_di(app, container, manage_lifespan=False)
    app.router.add_get("/", labels)
    return app, container


async def test_manage_lifespan_false_leaves_the_root_alone() -> None:
    finalized: list[str] = []
    app, container = build_unmanaged_app(finalized)

    async with TestClient(TestServer(app)) as client:
        response = await client.get("/")
        assert await response.text() == "app,request"
        assert finalized == ["request"]

    assert not container.closed
    assert finalized == ["request"]


async def test_manage_lifespan_false_does_not_reopen_a_closed_root() -> None:
    app, container = build_unmanaged_app([])
    container.close_sync()

    async with TestClient(TestServer(app)) as client:
        response = await client.get("/")
        assert response.status == http.HTTPStatus.INTERNAL_SERVER_ERROR

    assert container.closed


async def test_user_owned_root_runs_app_finalizer_once_at_exit() -> None:
    finalized: list[str] = []
    app, container = build_unmanaged_app(finalized)

    async with container:
        async with TestClient(TestServer(app)) as client:
            first = await client.get("/")
            second = await client.get("/")
            assert (await first.text(), await second.text()) == ("app,request", "app,request")
        assert finalized == ["request", "request"]

    assert finalized == ["request", "request", "app"]
