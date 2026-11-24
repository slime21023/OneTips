---
id: retry-with-backoff
summary: Cap retry attempts and delay for transient Acme SDK failures.
category: networking
tags: [retry]
related: [idempotency-keys]
applies_to:
  acme-sdk: '>=2.0 <3.0'
x-example: maximum-delay
---

# Retry with backoff

## When to Use

Retry only transient failures that are safe to repeat. See [idempotency keys](idempotency-keys.md).

## Recommended Approach

Use a capped delay and a fixed maximum attempt count.

```python status=tested
def retry_delay(attempt: int) -> int:
    return min(2 ** attempt, 8)


assert [retry_delay(i) for i in range(6)] == [1, 2, 4, 8, 8, 8]
```

```text
## 檢查清單
```

## Pitfalls

Do not retry permanent errors. The next fence illustrates an assertion that is not meant to be run.

```python status=unverified
raise AssertionError("unverified fences must not run")
```

## 檢查清單

- [ ] Limit both attempts and delay.
