# Benchmarks

Per-request latency of the framework itself. Every app is called in-process,
without a server or sockets (RSGI for rapis, ASGI for the others), so the
numbers show what each framework adds to a request.

## Run

```bash
uv run benchmarks/frameworks.py
```

`frameworks.py` declares its dependencies inline: uv builds a separate
environment with BlackSheep, Litestar and FastAPI and installs rapis from this
checkout, C module included.

`ROUNDS` and `N` (calls per batch) are read from the environment, e.g.
`ROUNDS=40 uv run benchmarks/frameworks.py`. Background load skews the
numbers; on macOS `taskpolicy -t 0 -l 0 uv run ...` keeps the run on the
performance cores.

## Method

- Every variant runs batches of `N` requests; batches of all variants are
  interleaved in random order, each one after a short warm-up.
- **ns per request, best**: the fastest of `ROUNDS` batches.
- **relative to rapis 0.1**: median over rounds of the ratio to rapis 0.1 in
  the same round. It holds up under background load better than absolute
  numbers.
- ASGI apps get a fresh scope for every request, as from a server; the cost
  of copying it is subtracted.
- Every scenario has its own app with only the routes it needs (`/`,
  `/items/{id}`, `/query`, …). Nothing else is registered, so a router with
  linear search is not charged for routes of other scenarios.
- In the path scenarios every request carries its own id, as in real traffic,
  so a route cache cannot answer instead of the router (BlackSheep keeps the
  last 1200 matches in an LRU cache).
- The handlers are the same everywhere: they take an `int` path parameter or
  `int`/`str` query parameters and answer 204 with an empty body. rapis 0.1,
  BlackSheep, Litestar and FastAPI return `None`; rapis 0.0.4 returns `""`,
  which gives the same empty body. FastAPI has `/docs` and `/openapi.json`
  turned off. Middleware passes the request through: request level in rapis
  and BlackSheep, pure ASGI (the cheapest kind) in Litestar and FastAPI.
- `rapis 0.1 (no C)` is the same rapis 0.1 app with the pure-Python query
  parser (`rapis/_query.py`) instead of the C module.
- `rapis 0.0.4` is the `0.0.4` tag (`git archive 0.0.4 rapis`) copied to
  `benchmarks/rapis004`, with its imports renamed from `rapis.` to `rapis004.`
  so both versions can be imported in one process. That release has no C
  module. It is measured with its own API: `WebApp`, `AppRouter`, `Query[T]`
  for query parameters, route middleware through `Middleware(cls)`. Its dynamic
  routes are matched by a linear scan over the route list, as in that release.

## Results

Apple M4, macOS 26.6.2, Python 3.12.14, default `ROUNDS`/`N`, 2026-10-12.
msgspec 0.22.0, BlackSheep 2.6.4, Litestar 2.24.0, FastAPI 0.143.0
(Starlette 1.7.0). rapis 0.1. rapis 0.0.4 is the tag.

ns per request, best (lower -> better):

| scenario                 | rapis     | rapis (no C)     | rapis 0.0.4 | BlackSheep | Litestar | FastAPI |
| ------------------------ | --------: | ---------------: | ----------: | ---------: | -------: | ------: |
| empty, 204               |       370 |              371 |         822 |       1426 |     7226 |   15551 |
| path, 1 dynamic route    |       834 |              835 |        1401 |       2604 |    10219 |   20951 |
| path, 50 dynamic routes  |       910 |              915 |        5838 |       7043 |    10323 |   36139 |
| path, 200 dynamic routes |       919 |              932 |       19804 |      20482 |    10335 |   80266 |
| query, 2 params          |       913 |             1049 |        2367 |       4456 |     9244 |   26181 |
| query, 6 params          |      1068 |             1348 |        4317 |      17204 |     9473 |   43233 |
| query, %-encoded         |       899 |             4119 |        4784 |       9279 |     9106 |   33100 |
| empty + 1 middleware     |       462 |              453 |         889 |       1554 |     7776 |   15847 |
| empty + 3 middleware     |       623 |              617 |        1027 |       1753 |     7948 |   15932 |
| empty + 5 middleware     |       780 |              780 |        1156 |       1970 |     8080 |   16294 |

relative to rapis (lower -> better):

| scenario                 | rapis     | rapis (no C)     | rapis 0.0.4 | BlackSheep | Litestar | FastAPI |
| ------------------------ | --------: | ---------------: | ----------: | ---------: | -------: | ------: |
| empty, 204               |      1.00 |             1.00 |        2.16 |       3.79 |    19.33 |   41.38 |
| path, 1 dynamic route    |      1.00 |             1.01 |        1.68 |       3.12 |    12.31 |   25.17 |
| path, 50 dynamic routes  |      1.00 |             1.00 |        6.15 |       7.42 |    11.04 |   38.24 |
| path, 200 dynamic routes |      1.00 |             1.01 |       20.88 |      21.59 |    11.04 |   84.61 |
| query, 2 params          |      1.00 |             1.16 |        2.58 |       4.90 |    10.05 |   28.48 |
| query, 6 params          |      1.00 |             1.25 |        4.02 |      15.89 |     8.82 |   40.10 |
| query, %-encoded         |      1.00 |             4.48 |        5.16 |      10.10 |     9.99 |   36.00 |
| empty + 1 middleware     |      1.00 |             0.99 |        1.89 |       3.32 |    16.83 |   34.00 |
| empty + 3 middleware     |      1.00 |             1.00 |        1.64 |       2.81 |    12.60 |   25.36 |
| empty + 5 middleware     |      1.00 |             1.00 |        1.48 |       2.50 |    10.35 |   20.70 |
