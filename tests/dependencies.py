import dataclasses

from aiohttp import web
from modern_di import Group, Scope, providers


@dataclasses.dataclass(kw_only=True, slots=True)
class SimpleCreator:
    dep1: str


@dataclasses.dataclass(kw_only=True, slots=True)
class DependentCreator:
    dep1: SimpleCreator


def fetch_method_from_request(request: web.Request) -> str:
    assert isinstance(request, web.Request)
    return request.method


class Dependencies(Group):
    app_factory = providers.Factory(creator=SimpleCreator, kwargs={"dep1": "original"})
    session_factory = providers.Factory(scope=Scope.SESSION, creator=DependentCreator, bound_type=None)
    request_factory = providers.Factory(scope=Scope.REQUEST, creator=DependentCreator, bound_type=None)
    request_method = providers.Factory(scope=Scope.REQUEST, creator=fetch_method_from_request, bound_type=None)
