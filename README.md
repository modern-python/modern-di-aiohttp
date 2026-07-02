<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)"  srcset="https://raw.githubusercontent.com/modern-python/.github/main/brand/projects/modern-di-aiohttp/lockup-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/modern-python/.github/main/brand/projects/modern-di-aiohttp/lockup-light.svg">
    <img alt="modern-di-aiohttp" src="https://raw.githubusercontent.com/modern-python/.github/main/brand/projects/modern-di-aiohttp/lockup.png" width="420">
  </picture>
</p>

[![PyPI version](https://img.shields.io/pypi/v/modern-di-aiohttp.svg)](https://pypi.org/project/modern-di-aiohttp/)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/modern-di-aiohttp.svg)](https://pypi.org/project/modern-di-aiohttp/)
[![Downloads](https://static.pepy.tech/badge/modern-di-aiohttp/month)](https://pepy.tech/projects/modern-di-aiohttp)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen.svg)](https://github.com/modern-python/modern-di-aiohttp/actions/workflows/ci.yml)
[![CI](https://github.com/modern-python/modern-di-aiohttp/actions/workflows/ci.yml/badge.svg)](https://github.com/modern-python/modern-di-aiohttp/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/modern-python/modern-di-aiohttp.svg)](https://github.com/modern-python/modern-di-aiohttp/blob/main/LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/modern-python/modern-di-aiohttp)](https://github.com/modern-python/modern-di-aiohttp/stargazers)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![ty](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ty/main/assets/badge/v0.json)](https://github.com/astral-sh/ty)

[Modern-DI](https://github.com/modern-python/modern-di) integration for [aiohttp](https://docs.aiohttp.org).

## Installation

```bash
uv add modern-di-aiohttp      # or: pip install modern-di-aiohttp
```

## Usage

aiohttp has no dependency-injection system of its own, so `modern-di-aiohttp` pairs an `@inject` decorator with inert `FromDI` markers. `setup_di` stores the container on the app, opens it on startup and closes it on cleanup, and installs middleware that builds a per-connection child container automatically; `FromDI` resolves a provider (or type) into a handler parameter.

```python
import dataclasses
import typing

from aiohttp import web
from modern_di import Container, Group, Scope, providers
from modern_di_aiohttp import FromDI, inject, setup_di


@dataclasses.dataclass(kw_only=True)
class Settings:
    debug: bool = True


@dataclasses.dataclass(kw_only=True)
class UserService:
    settings: Settings  # auto-injected by type


class Dependencies(Group):
    settings = providers.Factory(scope=Scope.APP, creator=Settings)
    user_service = providers.Factory(scope=Scope.REQUEST, creator=UserService)


@inject
async def index(
    request: web.Request,
    user_service: typing.Annotated[UserService, FromDI(Dependencies.user_service)],
) -> web.Response:
    return web.json_response({"debug": user_service.settings.debug})


app = web.Application()
app.router.add_get("/", index)
setup_di(app, Container(groups=[Dependencies], validate=True))
```

An HTTP request opens a `Scope.REQUEST` child container; a WebSocket connection opens a `Scope.SESSION` one. The connection `aiohttp.web.Request` is resolvable within DI: HTTP handlers and `REQUEST`-scoped factories inject it by type via `aiohttp_request_provider`, while WebSocket handlers read it via `FromDI(aiohttp_websocket_provider)`. For per-message work inside a WebSocket handler, open a nested `Scope.REQUEST` child of the session container fetched with `fetch_request_container`.

## API

| Symbol | Description |
|---|---|
| `setup_di(app, container)` | Stores the container on the app, wires `on_startup`/`on_cleanup` (reopen on startup, close on cleanup), registers the connection providers, and installs the per-connection middleware |
| `inject(handler)` | Decorator that resolves every `FromDI`-marked parameter from the request's child container and passes them to the handler |
| `FromDI(dependency)` | Inert `Annotated` marker resolved by `@inject`; accepts a provider or a type |
| `fetch_di_container(app)` | Returns the app-scoped root container |
| `fetch_request_container(request)` | Returns the per-connection child container the middleware built for this request |
| `aiohttp_request_provider` | `ContextProvider` for the current `aiohttp.web.Request` (`REQUEST` scope) |
| `aiohttp_websocket_provider` | `ContextProvider` for the connection `aiohttp.web.Request` at WebSocket `SESSION` scope |

## 📦 [PyPI](https://pypi.org/project/modern-di-aiohttp)

## 📝 [License](LICENSE)

## Part of `modern-python`

Built on [`modern-di`](https://github.com/modern-python/modern-di), a dependency-injection framework with IoC container and scopes.

Browse the full list of templates and libraries in
[`modern-python`](https://github.com/modern-python) — see the org profile for the categorized index.
