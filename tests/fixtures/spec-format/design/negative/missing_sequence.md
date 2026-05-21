# Design: Coffee Order API

## Overview

This document describes the architecture of the Coffee Order API service. It accepts orders and queues them.

## Data Flow

```mermaid
flowchart LR
    Customer --> API
    API --> Queue
```
