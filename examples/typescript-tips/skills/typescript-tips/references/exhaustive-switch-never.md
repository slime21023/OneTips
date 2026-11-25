---
id: exhaustive-switch-never
summary: Enforce exhaustive handling of discriminated unions using a never helper in the default branch.
category: style
tags: [type-safety, discriminated-union, switch]
related: [typed-result-pattern]
applies_to:
  typescript: '>=5.0'
---

# Exhaustive switch checks with never

## When to Use

Use this convention whenever switching over a closed discriminated union (events, states, error codes) so adding a new union member becomes a compile-time error until every `switch` handles it.

## Recommended Approach

Keep a single `assertNever` helper in your shared domain utilities:

```ts status=compiled
export function assertNever(value: never): never {
  throw new Error(`Unhandled discriminated union member: ${JSON.stringify(value)}`);
}
```

Call `assertNever` in the `default` branch instead of returning a fallback placeholder:

```ts status=tested
import assert from "node:assert/strict";

type JobState = { kind: "pending" } | { kind: "done"; output: string } | { kind: "failed"; reason: string };

function assertNever(value: never): never {
  throw new Error(`Unhandled state: ${JSON.stringify(value)}`);
}

function summarize(state: JobState): string {
  switch (state.kind) {
    case "pending":
      return "waiting";
    case "done":
      return `ok:${state.output}`;
    case "failed":
      return `err:${state.reason}`;
    default:
      return assertNever(state);
  }
}

assert.equal(summarize({ kind: "pending" }), "waiting");
assert.equal(summarize({ kind: "done", output: "42" }), "ok:42");
assert.equal(summarize({ kind: "failed", reason: "timeout" }), "err:timeout");
```

## Pitfalls

- Writing `default: return "unknown"` silently hides unhandled cases when a new variant is added to the union.
- Passing `value as never` defeats exhaustiveness checking and reintroduces runtime bugs.

## Checklist

- [ ] Closed union `switch` statements delegate `default` to `assertNever(value)` without casting.
- [ ] No silent fallback `default` hides newly added union variants.
