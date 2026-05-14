# Benchmarks

_benchmark was partially generated with ai, so framework apps may be not be in their "perfect form" any pull requests for this part of code are welcome_

Micro-benchmarks compare **rapis** with **Litestar**, **FastAPI**, **Emmett**, and **Sanic** (plus a **granian raw** RSGI baseline on Granian) using **oha** as the load generator.

## Methodology

- **Server**: Granian, single worker (`--workers 1`), WebSockets off (`--no-ws`), uvloop (if installed) else asyncio; **Sanic** uses its own server (`sanic` CLI, one worker).
- **Interfaces**: rapis, **granian raw**, and Emmett use **RSGI** on Granian; Litestar and FastAPI use **ASGI** on Granian.
- **Load**: `oha -z <duration> -c <connections>` against `127.0.0.1` (defaults from `benchmarks/config.py`).
- **Scenarios** (same sequence as in `benchmarks/run_benchmarks.py`)
  - **plain**: `GET /bench/plain` → small JSON body (`{"ok": true}`).
  - **validation**: `POST /bench/validate` with JSON body `{"name":"oha","count":42}`; **rapis** and **Sanic** use **msgspec** `Struct`; **Litestar** and **FastAPI** use **Pydantic v2**; **Emmett** uses a **`Form` / `Field()`** schema on the JSON body (see `emmett_bench.py`).
  - **static routing**: `GET /bench/r/<index>` with **`BENCH_ROUTE_COUNT` static routes** registered at import time (default **256**); the probe hits the middle route (`TARGET_ROUTE_INDEX = ROUTE_COUNT // 2`).
  - **dynamic routing**: `GET /bench/d/<index>` → one parameterized route (`<index>` is the middle value from `TARGET_ROUTE_INDEX`, same numeric target as in static routing, but matched as a single path pattern).
  - **large response**: `GET /bench/large` → JSON object with **`data`** set to a list of **1000** integers (`0 … 999`); exercises serialization of a heavier payload than **plain**.
  - **query params**: `GET /bench/query?skip=<TARGET_ROUTE_INDEX>&limit=10` → handler reads **`skip`** and **`limit`** as integers from the query string and returns them as JSON (`Query` helpers where the framework exposes them).

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
| Load duration `-z` | `10s` |
| Connections `-c` | `64` |
| Static routes (`BENCH_ROUTE_COUNT`) | `256` |
| Routing probe URL | `/bench/r/256` |
| Interfaces | rapis & Emmett: Granian RSGI; Litestar & FastAPI: Granian ASGI; Sanic: native server. |

#### Framework & library packages (PyPI)

| Package | Version |
|---------|---------|
| `rapis` | `0.0.4` |
| `sanic` | `25.12.0` |
| `litestar` | `2.21.1` |
| `fastapi` | `0.136.1` |
| `emmett` | `2.8.1` |
| `msgspec` | `0.21.1` |
| `pydantic` | `2.13.4` |

#### Scenario `plain`

| Framework | RPS | ratio | avg ms | p50 ms | p99 ms |
|-----------|-----|-------|--------|--------|--------|
| rapis | **198306.64** | **3.93** | **0.3218** | **0.3177** | **0.4587** |
| emmett | 133817.87 | 2.65 | 0.4772 | 0.4498 | 1.1929 |
| sanic | 77956.45 | 1.55 | 0.8203 | 0.826 | 1.2608 |
| litestar | 72013.55 | 1.43 | 0.8879 | 0.8635 | 1.4329 |
| fastapi async | 50447.56 | 1.00 | 1.2678 | 1.2075 | 3.0895 |
| fastapi sync | 9996.36 | 0.20 | 6.4026 | 6.0337 | 14.0203 |

#### Scenario `validation`

| Framework | RPS | ratio | avg ms | p50 ms | p99 ms |
|-----------|-----|-------|--------|--------|--------|
| rapis | **192928.51** | **7.97** | **0.3307** | **0.3259** | **0.4788** |
| emmett | 55866.05 | 2.31 | 1.1447 | 1.0892 | 2.9578 |
| sanic | 63036.64 | 2.60 | 1.0145 | 1.0089 | 1.2506 |
| litestar | 27838.62 | 1.15 | 2.2981 | 2.1423 | 11.891 |
| fastapi async | 24218.31 | 1.00 | 2.6419 | 2.3473 | 10.0476 |
| fastapi sync | 8494.18 | 0.35 | 7.5351 | 6.9086 | 16.5808 |

#### Scenario `static routing`

| Framework | RPS | ratio | avg ms | p50 ms | p99 ms |
|-----------|-----|-------|--------|--------|--------|
| rapis | **197192.74** | **33.28** | **0.3237** | **0.3176** | **0.4798** |
| emmett | 140307.39 | 23.68 | 0.4551 | 0.4508 | 0.5857 |
| sanic | 78597.28 | 13.26 | 0.8136 | 0.8225 | 1.2098 |
| litestar | 61197.05 | 10.33 | 1.045 | 1.0192 | 1.6675 |
| fastapi async | 5925.23 | 1.00 | 10.7963 | 10.3081 | 19.7209 |
| fastapi sync | 5992.44 | 1.01 | 10.6829 | 10.3666 | 18.747 |

#### Scenario `dynamic routing`

| Framework | RPS | ratio | avg ms | p50 ms | p99 ms |
|-----------|-----|-------|--------|--------|--------|
| rapis | **168258.75** | **26.95** | **0.3794** | **0.3513** | **0.9427** |
| emmett | 99861.57 | 15.99 | 0.6398 | 0.5833 | 1.597 |
| sanic | 35836.58 | 5.74 | 1.7851 | 1.7581 | 2.4663 |
| litestar | 62214.35 | 9.96 | 1.0278 | 1.0002 | 1.6964 |
| fastapi async | 6243.49 | 1.00 | 10.2528 | 10.0609 | 16.5024 |
| fastapi sync | 3648.9 | 0.58 | 17.5535 | 17.0571 | 26.9222 |

#### Scenario `large response`

| Framework | RPS | ratio | avg ms | p50 ms | p99 ms |
|-----------|-----|-------|--------|--------|--------|
| rapis | **186782.81** | **7.54** | **0.3417** | **0.3309** | **0.6913** |
| emmett | 41271.04 | 1.67 | 1.5497 | 1.4856 | 3.4429 |
| sanic | 26216.67 | 1.06 | 2.4404 | 2.4003 | 3.7425 |
| litestar | 35693.85 | 1.44 | 1.7922 | 1.7712 | 2.717 |
| fastapi async | 24778.4 | 1.00 | 2.5819 | 2.5582 | 3.3108 |
| fastapi sync | 2364.08 | 0.10 | 27.1053 | 25.9484 | 41.7312 |

#### Scenario `query params`

| Framework | RPS | ratio | avg ms | p50 ms | p99 ms |
|-----------|-----|-------|--------|--------|--------|
| rapis | **183238.34** | **6.08** | **0.3483** | **0.337** | **0.696** |
| emmett | 90679.83 | 3.01 | 0.7049 | 0.6938 | 0.8605 |
| sanic | 63636.51 | 2.11 | 1.005 | 0.9881 | 1.4748 |
| litestar | 59306.13 | 1.97 | 1.0783 | 1.0483 | 1.7797 |
| fastapi async | 30139.06 | 1.00 | 2.1225 | 2.0853 | 3.476 |
| fastapi sync | 8726.64 | 0.29 | 7.3341 | 6.9348 | 15.3996 |

<!-- BENCHMARK_AUTO_END -->
---

## Repository layout

| Path | Role |
|------|------|
| `benchmarks/apps/` | Minimal apps per framework (shared routes). |
| `benchmarks/run_benchmarks.py` | Starts Granian + runs **oha**, writes `benchmarks/results.json`. |
| `benchmarks/render_readme.py` | Regenerates README tables from `benchmarks/results.json`. |
| `benchmarks/config.py` | Tunables via environment variables. |
