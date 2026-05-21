# Bugfix: Order id is null on retry

## Expected Behavior

- When the customer retries an order with the same idempotency key, the system shall return the original order id.

## Unchanged Behavior

- Fresh orders without an idempotency key continue to receive a new order id.
