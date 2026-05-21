# Design: Coffee Order API

## Sequence

```mermaid
sequenceDiagram
    participant C as Customer
    participant A as API
    C->>A: POST /orders
    A-->>C: 201
```

## Data Flow

```mermaid
flowchart LR
    Customer --> API
    API --> Queue
```
