# Design: Coffee Order API

## Overview

This document describes the architecture of the Coffee Order API service.

## Sequence

```mermaid
sequenceDiagram
    participant C as Customer
    participant A as API
    C->>A: POST /orders
    A-->>C: 201
```
