# Benchmarks

_benchmark was partially generated with ai, so framework apps may be not be in their "perfect form" any pull requests for this part of code are welcome_

Micro-benchmarks compare **rapis** with **Litestar**, **FastAPI**, and **Emmett** under the same HTTP server (**Granian**) and load generator (**oha**).

## Methodology

- **Server**: Granian, single worker (`--workers 1`), WebSockets off (`--no-ws`), uvloop(if installed else asyncio) loop.
- **Interfaces**: rapis and Emmett use **RSGI**; Litestar and FastAPI use **ASGI** (Granian supports both).
- **Load**: `oha -z <duration> -c <connections>` against `127.0.0.1` (defaults from `benchmarks/config.py`).
- **Scenarios**
  - **plain**: `GET /bench/plain` → small JSON body (`{"ok":…}`).
  - **validation**: `POST /bench/validate` with JSON payload; rapis validates via **msgspec** `Struct`; Litestar/FastAPI/Emmett via **Pydantic v2**.
  - **static routing**: `GET /bench/r/<index>` with **`BENCH_ROUTE_COUNT` static routes** registered at import time (default **256**); the probe hits the middle route (`TARGET_ROUTE_INDEX = ROUTE_COUNT // 2`).

## Run locally

```bash
pip install -e .
pip install -r benchmarks/requirements.txt
# optional: unset NO_COLOR if your shell sets it (oha parses --no-color strictly)
unset NO_COLOR

export BENCH_DURATION=15s      # optional
export BENCH_CONNECTIONS=40    # optional
export BENCH_ROUTE_COUNT=256    # optional

python benchmarks/run_benchmarks.py
python benchmarks/render_readme.py
```

---

<!-- BENCHMARK_AUTO_START -->

_Latest automated numbers (workflow «Benchmarks»)._

#### Runtime & load

| Field | Value |
|-------|-------|
| Python | `3.12.13` |
| Granian | `granian 2.7.4` |
| oha | `oha 1.14.0` |
| Load duration `-z` | `12s` |
| Connections `-c` | `64` |
| Static routes (`BENCH_ROUTE_COUNT`) | `256` |
| Routing probe URL | `/bench/r/128` |
| Interfaces | rapis & Emmett: Granian RSGI; Litestar & FastAPI: Granian ASGI. |

#### Framework & library packages (PyPI)

| Package | Version |
|---------|---------|
| `rapis` | `0.0.4` |
| `litestar` | `2.21.1` |
| `fastapi` | `0.136.1` |
| `emmett` | `2.8.1` |
| `msgspec` | `0.21.1` |
| `pydantic` | `2.13.4` |

#### Scenario `plain`

| Framework | RPS | avg ms | p50 ms | p99 ms |
|-----------|-----|--------|--------|--------|
| rapis | 197772.07 | 0.3226 | 0.3177 | 0.4695 |
| emmett | 147205.28 | 0.4338 | 0.4304 | 0.549 |
| litestar | 73123.67 | 0.8745 | 0.8665 | 1.0514 |
| fastapi async | 53945.31 | 1.1856 | 1.183 | 1.3564 |
| fastapi sync | 10156.66 | 6.3012 | 5.9608 | 12.6357 |

#### Scenario `validation`

| Framework | RPS | avg ms | p50 ms | p99 ms |
|-----------|-----|--------|--------|--------|
| rapis | 194014.5 | 0.3288 | 0.3245 | 0.474 |
| emmett | 57531.01 | 1.1117 | 1.0758 | 1.32 |
| litestar | 28863.96 | 2.2165 | 2.1061 | 8.7718 |
| fastapi async | 24527.25 | 2.6086 | 2.3411 | 8.8407 |
| fastapi sync | 8963.03 | 7.1418 | 6.7808 | 13.796 |

#### Scenario `static routing`

| Framework | RPS | avg ms | p50 ms | p99 ms |
|-----------|-----|--------|--------|--------|
| rapis | 190539.11 | 0.335 | 0.3257 | 0.556 |
| emmett | 141528.59 | 0.4512 | 0.4477 | 0.572 |
| litestar | 63728.0 | 1.0036 | 0.9977 | 1.1599 |
| fastapi async | 7543.79 | 8.4852 | 8.164 | 15.5986 |
| fastapi sync | 7662.54 | 8.3532 | 8.1199 | 14.5069 |

<!-- BENCHMARK_AUTO_END -->
---

## Repository layout

| Path | Role |
|------|------|
| `benchmarks/apps/` | Minimal apps per framework (shared routes). |
| `benchmarks/run_benchmarks.py` | Starts Granian + runs **oha**, writes `benchmarks/results.json`. |
| `benchmarks/render_readme.py` | Regenerates README tables from `benchmarks/results.json`. |
| `benchmarks/config.py` | Tunables via environment variables. |
