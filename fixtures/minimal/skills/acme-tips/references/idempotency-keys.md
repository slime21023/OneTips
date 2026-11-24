---
id: idempotency-keys
summary: Reuse the same idempotency key when retrying an Acme SDK request.
category: networking
tags: [idempotency]
related: [retry-with-backoff]
applies_to:
  acme-sdk: '>=2.0 <3.0'
---

# Idempotency keys

## When to Use

Use a key when a request might be repeated. See [retry with backoff](retry-with-backoff.md#檢查清單).

## Recommended Approach

Create a key once for the operation; reuse it for each attempt.

```python status=compiled
from uuid import uuid4

key = str(uuid4())
```

## Pitfalls

Do not make a new key for each attempt.

## 檢查清單

- [ ] Reuse the same key for the same operation.
