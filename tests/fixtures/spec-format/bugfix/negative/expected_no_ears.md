# Bugfix: Order id is null on retry

## Current Behavior

When the order POST is retried after a transient 500, the second response returns `order_id: null` even though the order persisted.

## Expected Behavior

- The retry should return the original order id.
- Idempotency keys should be case-sensitive.

## Unchanged Behavior

- Fresh orders without an idempotency key continue to receive a new order id.
