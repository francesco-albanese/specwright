# Design: Coffee Order API

## Overview

This document describes the architecture of the Coffee Order API service. It accepts orders from customers, queues them for baristas, and persists each order for audit.

## Sequence

```mermaid
sequenceDiagram
    participant C as Customer
    participant A as API
    participant Q as Queue
    C->>A: POST /orders
    A->>Q: enqueue(order)
    A-->>C: 201 + order_id
```

## Data Flow

```mermaid
flowchart LR
    Customer --> API
    API --> Queue
    Queue --> Barista
    API --> AuditLog
```
