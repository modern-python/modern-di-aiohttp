# Architecture

The living truth about what `modern-di-aiohttp` does **now**. One file per
capability, plus a single [`glossary.md`](glossary.md) (the ubiquitous
language) — living prose, no frontmatter, dated by git.

**Promotion rule:** when a change alters a capability's behavior, the
implementing PR hand-edits the matching `architecture/<capability>.md` in the
same diff, alongside the code. The *why* lives in the change bundle under
[`planning/changes/`](../planning/changes/).

## Capabilities

- [`container-lifecycle.md`](container-lifecycle.md) — wiring the container into
  the app, the `on_startup`/`on_cleanup` signal wiring, and the per-connection
  scoped child container built by `_di_middleware`.
- [`dependency-resolution.md`](dependency-resolution.md) — `FromDI` + the
  `@inject` decorator.
- [`glossary.md`](glossary.md) — the ubiquitous language.
