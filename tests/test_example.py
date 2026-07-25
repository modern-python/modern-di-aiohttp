import collections.abc
import http

from aiohttp import web
from aiohttp.test_utils import TestClient

from examples.app import app


AiohttpClient = collections.abc.Callable[[web.Application], collections.abc.Awaitable[TestClient]]


async def test_example_greets_by_name(aiohttp_client: AiohttpClient) -> None:
    client = await aiohttp_client(app)
    response = await client.get("/greet/world")
    assert response.status == http.HTTPStatus.OK
    assert await response.text() == "Hello, world!"
