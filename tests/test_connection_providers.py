from aiohttp import web

from modern_di_aiohttp import aiohttp_request_provider
from modern_di_aiohttp.main import _CONNECTION_PROVIDERS


def test_exactly_one_connection_provider_is_registered_by_type() -> None:
    """INVARIANT: only ``aiohttp_request_provider`` carries a bound type; the rest are reference-only.

    Broken by dropping ``bound_type=None`` from ``aiohttp_websocket_provider``, or by adding a
    second type-bound connection provider. aiohttp hands the middleware a ``web.Request`` for both
    connection kinds -- a WebSocket is an upgraded HTTP GET, not a distinct object -- while
    modern-di's providers registry admits one provider per bound type, so a second type-bound
    connection provider makes ``setup_di`` raise ``DuplicateProviderTypeError`` for every
    application built. Reference-only is what lets a ``SESSION``-scoped connection provider exist
    at all, and the reason the WebSocket path reads the connection by provider reference instead of
    by bare type (ADR 0001).
    """
    assert {provider.context_type for provider in _CONNECTION_PROVIDERS} == {web.Request}

    type_bound = [provider for provider in _CONNECTION_PROVIDERS if provider.bound_type is not None]

    assert type_bound == [aiohttp_request_provider]
