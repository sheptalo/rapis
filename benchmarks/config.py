import os

ROUTE_COUNT = int(os.environ.get("BENCH_ROUTE_COUNT", "256"))
TARGET_ROUTE_INDEX = max(0, ROUTE_COUNT // 2)
BENCH_DURATION = os.environ.get("BENCH_DURATION", "12s")
BENCH_CONNECTIONS = int(os.environ.get("BENCH_CONNECTIONS", "64"))

GRANIAN_EXTRA_ARGS = os.environ.get(
    "GRANIAN_EXTRA_ARGS",
    "--workers 1 --no-ws",
).split()
