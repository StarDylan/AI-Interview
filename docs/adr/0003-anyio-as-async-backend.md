# 3. AnyIO as Async Backend

Date: 2025-08-16

## Status

Accepted

## Context

We need to select an async backend for this project because of the many complex real-time requirements. The main options were Trio, asyncio, and AnyIO.

Trio provides excellent structured concurrency semantics, but it has limited ecosystem support. Many major event loop runners, such as uvicorn, do not support Trio directly.  
asyncio is the default Python async library and has strong ecosystem support, but its semantics are less ergonomic than Trio.  
AnyIO provides Trio-like structured concurrency semantics while running on either asyncio or Trio, giving us both better developer experience and compatibility with existing tooling like uvicorn.

## Decision

We will use AnyIO as the async backend. This gives us the developer-friendly semantics of Trio while maintaining compatibility with the asyncio ecosystem, including uvicorn.

## Consequences

- We can run clean, structured async code with safer concurrency patterns.
- We retain compatibility with asyncio-native libraries and uvicorn.
- We cannot mix Trio-only libraries when running on asyncio.
- Developers need to be aware of AnyIO’s cancellation and task group semantics, which differ slightly from raw asyncio.
