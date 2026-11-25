---
id: layered-module-layout
summary: Separate pure TypeScript domain logic from I/O adapters and entrypoints with one-way imports.
category: architecture
tags: [architecture, layering, modules]
related: [typed-result-pattern, runtime-config-loader]
applies_to:
  typescript: '>=5.0'
---

# Layered module layout for TypeScript services

## When to Use

Use this layout when a TypeScript package or service combines business rules with external I/O (HTTP, database, filesystem, environment variables) and you want domain logic testable without mocks. Skip it for single-file scripts.

## Recommended Approach

Keep dependencies pointing strictly inward (`app -> adapters -> domain`):

```text
src/
  domain/       Pure types, validation rules, and state transitions (no I/O imports)
  adapters/     Filesystem, HTTP, database, and env readers returning domain types
  app/          Use-case orchestration and CLI/HTTP entrypoints
tests/
  domain/       Fast unit tests with in-memory data
  integration/  Tests exercising adapters and app entrypoints
```

Pair domain return types with the [typed result pattern](typed-result-pattern.md#checklist) and isolate environment parsing using the [runtime config loader](runtime-config-loader.md#recommended-approach).

## Pitfalls

- Importing `node:fs`, `process.env`, or SDK clients inside `src/domain/` makes unit tests slow and tightly coupled.
- Creating pass-through wrapper layers that only re-export another module adds indirection without clarity.

## Checklist

- [ ] Files under `src/domain/` do not import runtime I/O modules or `src/adapters/`.
- [ ] Entrypoints under `src/app/` handle formatting and exit/status codes rather than domain rules.
- [ ] Each boundary converts external data into explicit domain types once at the adapter edge.
