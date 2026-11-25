---
id: typed-result-pattern
summary: Use a discriminated Result<T, E> union for expected failures instead of untyped thrown errors.
category: templates
tags: [error-handling, result, discriminated-union]
related: [exhaustive-switch-never, layered-module-layout]
applies_to:
  typescript: '>=5.0'
---

# Typed Result union thin template

## When to Use

Use this thin template in domain or parsing functions where callers must handle failure cases explicitly (validation errors, missing records, malformed input). Reserve `throw` for unexpected bugs or unrecoverable I/O failures.

## Recommended Approach

Define a minimal discriminated union with `ok` and `err` constructors, then replace `ParseError` and `parsePort` with your domain error union and parser:

```ts status=tested
import assert from "node:assert/strict";

export type Result<T, E> = { readonly ok: true; readonly value: T } | { readonly ok: false; readonly error: E };

export const ok = <T>(value: T): Result<T, never> => ({ ok: true, value });
export const err = <E>(error: E): Result<never, E> => ({ ok: false, error });

type ParseError = { readonly code: "INVALID_PORT"; readonly raw: string };

function parsePort(raw: string): Result<number, ParseError> {
  const port = Number(raw);
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    return err({ code: "INVALID_PORT", raw });
  }
  return ok(port);
}

const good = parsePort("8080");
assert.equal(good.ok, true);
if (good.ok) assert.equal(good.value, 8080);

const bad = parsePort("99999");
assert.equal(bad.ok, false);
if (!bad.ok) assert.equal(bad.error.code, "INVALID_PORT");
```

## Pitfalls

- Do not use `string` as the error type `E` across multiple failure modes; use a discriminated object union so callers can branch safely.
- Avoid wrapping every third-party exception in `Result` blindly; distinguish expected domain errors from programmer bugs.

## Checklist

- [ ] `Result<T, E>` uses a boolean discriminant (`ok: true | false`) with `readonly` properties.
- [ ] Domain error types carry a stable `code` discriminant rather than free-form message matching.
- [ ] Callers narrow on `result.ok` before accessing `value` or `error`.
