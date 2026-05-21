# Bugfix: Order id is null on retry

## Current Behavior

When the order POST is retried after a transient 500, the second response returns `order_id: null` even though the order persisted.

## Expected Behavior

- When the customer retries an order with the same idempotency key, the system shall return the original order id.
