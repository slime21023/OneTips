---
id: runtime-config-loader
summary: Parse and validate environment variables once at startup into a frozen typed config object.
category: templates
tags: [config, env, startup]
related: [layered-module-layout, typed-result-pattern]
applies_to:
  typescript: '>=5.0'
  node: '>=20.0'
  bun: '>=1.0'
---

# Runtime config loader thin template

## When to Use

Use this thin template at the adapter edge to convert `process.env` into a typed configuration object before starting the application. Adapt the fields in `AppConfig` to your service.

## Recommended Approach

Accept an injected `Record<string, string | undefined>` map so the loader is testable without mutating `process.env`:

```ts status=tested
import assert from "node:assert/strict";

export interface AppConfig {
  readonly port: number;
  readonly logLevel: "debug" | "info" | "warn" | "error";
}

const LOG_LEVELS = new Set<AppConfig["logLevel"]>(["debug", "info", "warn", "error"]);

export function loadConfig(env: Readonly<Record<string, string | undefined>>): AppConfig {
  const rawPort = env.PORT ?? "3000";
  const port = Number(rawPort);
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new Error(`Invalid PORT: ${rawPort}`);
  }
  const level = (env.LOG_LEVEL ?? "info") as AppConfig["logLevel"];
  if (!LOG_LEVELS.has(level)) {
    throw new Error(`Invalid LOG_LEVEL: ${level}`);
  }
  return Object.freeze({ port, logLevel: level });
}

const config = loadConfig({ PORT: "4000", LOG_LEVEL: "debug" });
assert.deepEqual(config, { port: 4000, logLevel: "debug" });
assert.throws(() => loadConfig({ PORT: "abc" }), /Invalid PORT/);
```

## Pitfalls

- Reading `process.env` directly inside business logic scatters defaults and makes missing variables fail late at runtime.
- Casting `env.PORT as unknown as number` skips validation and silently passes `NaN` or strings downstream.

## Checklist

- [ ] `loadConfig` accepts an explicit `env` record rather than hard-coding `process.env` inside the parser.
- [ ] Missing or malformed required values fail fast at startup with a clear variable name.
- [ ] Returned config object is immutable (`readonly` fields and `Object.freeze`).
