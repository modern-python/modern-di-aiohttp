import modern_di
import pytest
from aiohttp import web

from modern_di_aiohttp import setup_di
from tests.dependencies import Dependencies


@pytest.fixture
def app() -> web.Application:
    application = web.Application()
    container = modern_di.Container(groups=[Dependencies])
    setup_di(application, container)
    return application
