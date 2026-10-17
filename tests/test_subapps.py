import collections.abc
import dataclasses
import http
import typing

from aiohttp import web
from aiohttp.test_utils import TestClient
from modern_di import Container, Group, Scope, providers
from modern_di.providers import CacheSettings

from modern_di_aiohttp import FromDI, fetch_request_container, inject, setup_di


AiohttpClient = collections.abc.Callable[[web.Application], collections.abc.Awaitable[TestClient]]


@dataclasses.dataclass(kw_only=True, slots=True)
class Label:
    name: str


def make_group(name: str, finalized: list[str]) -> type[Group]:
    class AppDependencies(Group):
        label = providers.Factory(
            scope=Scope.REQUEST,
            creator=lambda: Label(name=name),
            bound_type=Label,
            cache=CacheSettings(finalizer=lambda label: finalized.append(label.name)),
        )

    return AppDependencies


@inject
async def label_view(
    request: web.Request,  # noqa: ARG001
    label: typing.Annotated[Label, FromDI(Label)],
) -> web.Response:
    return web.Response(text=label.name)


@web.middleware
async def resolve_label_middleware(
    request: web.Request,
    handler: typing.Callable[[web.Request], typing.Awaitable[web.StreamResponse]],
) -> web.StreamResponse:
    fetch_request_container(request).resolve(Label)
    return await handler(request)


def build_apps(*, sub_has_di: bool, finalized: list[str]) -> web.Application:
    sub = web.Application()
    sub.router.add_get("/x", label_view)
    if sub_has_di:
        setup_di(sub, Container(groups=[make_group("sub", finalized)]))

    parent = web.Application()
    parent.router.add_get("/x", label_view)
    setup_di(parent, Container(groups=[make_group("parent", finalized)]))
    parent.middlewares.append(resolve_label_middleware)
    parent.add_subapp("/sub", sub)
    return parent


async def test_each_app_resolves_from_its_own_container(aiohttp_client: AiohttpClient) -> None:
    client = await aiohttp_client(build_apps(sub_has_di=True, finalized=[]))

    parent_response = await client.get("/x")
    assert parent_response.status == http.HTTPStatus.OK
    assert await parent_response.text() == "parent"

    sub_response = await client.get("/sub/x")
    assert sub_response.status == http.HTTPStatus.OK
    assert await sub_response.text() == "sub"


async def test_sub_app_without_setup_di_resolves_from_parent(aiohttp_client: AiohttpClient) -> None:
    client = await aiohttp_client(build_apps(sub_has_di=False, finalized=[]))

    response = await client.get("/sub/x")
    assert response.status == http.HTTPStatus.OK
    assert await response.text() == "parent"


async def test_both_child_containers_closed_after_sub_app_request(aiohttp_client: AiohttpClient) -> None:
    finalized: list[str] = []
    client = await aiohttp_client(build_apps(sub_has_di=True, finalized=finalized))

    assert (await client.get("/sub/x")).status == http.HTTPStatus.OK
    assert sorted(finalized) == ["parent", "sub"]
