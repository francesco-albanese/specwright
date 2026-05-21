# Requirements: Coffee Order API

## Acceptance Criteria

- The system shall persist every order for at least 30 days.
- When the customer submits a valid order, the system shall return an order id within 200 ms.
- While the kitchen queue is full, the system shall reject new orders with HTTP 503.
