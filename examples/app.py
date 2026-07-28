# Minimal modern-di + aiohttp example.
# Run for real: python -m examples.app  (then GET http://localhost:8080/greet/world)
import dataclasses
import typing

from aiohttp import web
from modern_di import Container, Group, Scope, providers

from modern_di_aiohttp import FromDI, inject, setup_di


@dataclasses.dataclass(kw_only=True)
class Settings:
    greeting: str = "Hello"


@dataclasses.dataclass(kw_only=True)
class GreetingService:
    settings: Settings  # auto-injected by type

    def greet(self, name: str) -> str:
        return f"{self.settings.greeting}, {name}!"


class Dependencies(Group):
    settings = providers.Factory(scope=Scope.APP, creator=Settings)
    service = providers.Factory(scope=Scope.REQUEST, creator=GreetingService)


@inject
async def greet(
    request: web.Request,
    service: typing.Annotated[GreetingService, FromDI(Dependencies.service)],
) -> web.Response:
    name = request.match_info["name"]
    return web.Response(text=service.greet(name))


app = web.Application()
app.router.add_get("/greet/{name}", greet)
container = Container(groups=[Dependencies])
setup_di(app, container)
container.validate()  # optional fail-fast; must come after setup_di registers its providers


if __name__ == "__main__":
    web.run_app(app)  # pragma: no cover -- boot line, not exercised by the smoke test
