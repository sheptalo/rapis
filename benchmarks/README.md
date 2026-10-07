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
- **relative to rapis**: median over rounds of the ratio to rapis in the same
  round. It holds up under background load better than absolute numbers.
- ASGI apps get a fresh scope for every request, as from a server; the cost
  of copying it is subtracted.
- In the path scenarios every request carries its own id, as in real traffic,
  so a route cache cannot answer instead of the router (BlackSheep keeps the
  last 1200 matches in an LRU cache).
- The handlers are the same everywhere: they return `None` (204) and take an
  `int` path parameter or `int`/`str` query parameters. FastAPI has `/docs`
  and `/openapi.json` turned off. Middleware passes the request through:
  request level in rapis and BlackSheep, pure ASGI (the cheapest kind) in
  Litestar and FastAPI.
- `rapis (no C)` is the same rapis app with the pure-Python query parser
  (`rapis/_query.py`) instead of the C module.

## Results

Apple M4, macOS 26, Python 3.12.14, default `ROUNDS`/`N`, 2026-10-01.
msgspec 0.22.0, BlackSheep 2.6.3, Litestar 2.24.0, FastAPI 0.142.2
(Starlette 1.7.0).

ns overhead per request, best (lower -> better):

| scenario                 | rapis | rapis (no C) | BlackSheep | Litestar | FastAPI |
| ------------------------ | ----: | -----------: | ---------: | -------: | ------: |
| empty, 204               |   554 |          540 |       1416 |     7278 |   15472 |
| path, 1 dynamic route    |  1064 |         1057 |       3107 |    10139 |   21139 |
| path, 50 dynamic routes  |  1137 |         1135 |       6912 |    10082 |   35523 |
| path, 200 dynamic routes |  1141 |         1118 |      19869 |    10112 |   78958 |
| query, 2 params          |  1052 |         1184 |       4424 |     9000 |   27123 |
| query, 6 params          |  1241 |         1481 |      17122 |     9481 |   45137 |
| query, %-encoded         |  1055 |         4246 |       9195 |     9157 |   34167 |
| empty + 1 middleware     |   623 |          620 |       1517 |     7867 |   15645 |
| empty + 3 middleware     |   794 |          797 |       1758 |     7933 |   15897 |
| empty + 5 middleware     |   957 |          968 |       1968 |     8077 |   16222 |

relative to rapis(lower -> better):

| scenario                 | rapis (no C) | BlackSheep | Litestar | FastAPI |
| ------------------------ | -----------: | ---------: | -------: | ------: |
| empty, 204               |         1.00 |       2.61 |    13.30 |   28.37 |
| path, 1 dynamic route    |         1.00 |       2.90 |     9.40 |   19.73 |
| path, 50 dynamic routes  |         1.00 |       6.00 |     8.85 |   30.82 |
| path, 200 dynamic routes |         1.00 |      16.93 |     8.83 |   67.06 |
| query, 2 params          |         1.12 |       4.21 |     8.59 |   26.15 |
| query, 6 params          |         1.19 |      13.66 |     7.62 |   35.92 |
| query, %-encoded         |         4.01 |       8.61 |     8.61 |   32.25 |
| empty + 1 middleware     |         1.00 |       2.44 |    12.48 |   25.05 |
| empty + 3 middleware     |         1.00 |       2.22 |    10.02 |   19.86 |
| empty + 5 middleware     |         1.00 |       2.06 |     8.39 |   16.84 |
