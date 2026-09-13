# AGENTS.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`modern-di-aiohttp` is the [`modern-di`](https://github.com/modern-python/modern-di) integration for
[aiohttp](https://docs.aiohttp.org); [`CONTEXT.md`](CONTEXT.md) opens with what it does and owns the
vocabulary — read it before naming a concept in code, a test name, or an issue title. It is one of
that project's integrations, each of which lives in a separate repository and ships as a separate
PyPI package.

## Commands

`just` (task runner) and `uv` (package manager). The [`justfile`](justfile) is the source of truth —
`just --list`, or read it.

## Architecture

All implementation is `modern_di_aiohttp/main.py`, short enough to read whole. Read it.

### Testing patterns

`tests/dependencies.py` is the provider model every test builds on. Tests drive a real server
through pytest-aiohttp's `aiohttp_client` fixture, WebSockets included; `make_mocked_request` is for
the one case that has to bypass the middleware.

## Workflow

Every link in `README.md` must be absolute: `https://github.com/modern-python/<repo>/blob/main/<path>`,
or `.../tree/main/<path>` for a directory. Never a relative path: `README.md` is also the PyPI long
description, and PyPI does not rewrite relative links, so a relative one 404s on the package page.
