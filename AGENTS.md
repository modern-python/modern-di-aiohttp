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

All implementation is `modern_di_aiohttp/main.py`, short enough to read whole. Read it, and
[`docs/adr/`](docs/adr/) for why the connection is exposed the way it is.

### Testing patterns

`tests/dependencies.py` is the provider model every test builds on. Tests drive a real server
through pytest-aiohttp's `aiohttp_client` fixture, WebSockets included; `make_mocked_request` is for
the one case that has to bypass the middleware.

## Workflow

Real work **not scheduled** becomes a GitHub issue.

An invariant is a test whose name is the claim, with a docstring opening `INVARIANT:` and a second
paragraph naming **what breaks it** — design rationale, not a report of what this one test catches.
Nothing enforces that docstring shape; it is read at review time.
