import json
import os
import platform
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from importlib.metadata import PackageNotFoundError, version as dist_version
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(REPO_ROOT))

from benchmarks.config import (  # noqa: E402
    BENCH_CONNECTIONS,
    BENCH_DURATION,
    GRANIAN_EXTRA_ARGS,
    TARGET_ROUTE_INDEX,
)

GRANIAN_EXE = shutil.which("granian") or str(
    Path(sys.executable).parent / "granian"
)

FRAMEWORKS: list[dict[str, str]] = [
    {
        "id": "rapis",
        "target": "benchmarks.apps.rapis_bench:app",
        "interface": "rsgi",
    },
    {
        "id": "litestar",
        "target": "benchmarks.apps.litestar_bench:app",
        "interface": "asgi",
    },
    {
        "id": "fastapi async",
        "target": "benchmarks.apps.fastapi_bench:app",
        "interface": "asgi",
    },
    {
        "id": "fastapi sync",
        "target": "benchmarks.apps.fastapi_sync_bench:app",
        "interface": "asgi",
    },
    {
        "id": "emmett",
        "target": "benchmarks.apps.emmett_bench:app",
        "interface": "rsgi",
    },
]

SCENARIOS: list[dict[str, Any]] = [
    {
        "id": "plain",
        "method": "GET",
        "path": "/bench/plain",
        "body": None,
        "content_type": None,
    },
    {
        "id": "validation",
        "method": "POST",
        "path": "/bench/validate",
        "body": '{"name":"oha","count":42}',
        "content_type": "application/json",
    },
    {
        "id": "static routing",
        "method": "GET",
        "path": f"/bench/r/{TARGET_ROUTE_INDEX}",
        "body": None,
        "content_type": None,
    },
]


def pick_port() -> int:
    import socket

    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def wait_ready(host: str, port: int, timeout: float = 45.0) -> None:
    """Wait until Granian accepts TCP and speaks HTTP.

    ``urllib.error.HTTPError`` subclasses ``OSError``. Treating bare
    ``OSError`` as \"not listening yet\" accidentally retries forever on any
    HTTP error status (404/405/500), which surfaces as misleading timeouts when
    only rapis misroutes or rejects the probe request for subtle reasons.
    """
    deadline = time.monotonic() + timeout
    url = f"http://{host}:{port}/bench/plain"
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1.0)
        except urllib.error.HTTPError:
            # Stack returned an HTTP response — port is bound and Granian runs.
            return
        except OSError:
            time.sleep(0.05)
        else:
            return
    raise TimeoutError(url)


def parse_oha(raw: dict[str, Any]) -> dict[str, Any]:
    s = raw["summary"]
    p = raw["latencyPercentiles"]
    return {
        "rps": round(s["requestsPerSec"], 2),
        "avg_ms": round(s["average"] * 1000, 4),
        "p50_ms": round(p["p50"] * 1000, 4),
        "p99_ms": round(p["p99"] * 1000, 4),
    }


def run_oha(
    url: str, method: str, body: str | None, ctype: str | None
) -> dict[str, Any]:
    oha = shutil.which("oha")
    if not oha:
        raise RuntimeError(
            "oha executable not found (install https://github.com/hatoo/oha)"
        )

    env = os.environ.copy()
    env.pop("NO_COLOR", None)

    tmp = Path(tempfile.mkdtemp(prefix="oha_"))
    out = tmp / "out.json"
    cmd = [
        oha,
        url,
        "-z",
        BENCH_DURATION,
        "-c",
        str(BENCH_CONNECTIONS),
        "--no-tui",
        "-o",
        str(out),
        "--output-format",
        "json",
        "-m",
        method,
    ]
    if body is not None:
        cmd.extend(["-d", body])
    if ctype:
        cmd.extend(["-T", ctype])

    subprocess.run(cmd, check=True, env=env)
    raw = json.loads(out.read_text())
    shutil.rmtree(tmp, ignore_errors=True)
    return parse_oha(raw)


def bench_one(fw: dict[str, str], scenario: dict[str, Any]) -> dict[str, Any]:
    host = "127.0.0.1"
    port = pick_port()
    cmd = [
        GRANIAN_EXE,
        fw["target"],
        "--interface",
        fw["interface"],
        "--host",
        host,
        "--port",
        str(port),
        *GRANIAN_EXTRA_ARGS,
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    env.pop("NO_COLOR", None)

    log_dir = Path(tempfile.mkdtemp(prefix="granian_bench_"))
    granian_stderr = log_dir / "granian.stderr.log"

    stderr_fp = granian_stderr.open("w", encoding="utf-8", errors="replace")
    proc = subprocess.Popen(
        cmd,
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=stderr_fp,
    )
    path = scenario["path"]
    url = f"http://{host}:{port}{path}"
    try:
        wait_ready(host, port)
        metrics = run_oha(
            url,
            scenario["method"],
            scenario["body"],
            scenario["content_type"],
        )
        return {"ok": True, **metrics}
    except Exception as exc:
        tail = ""
        try:
            tail = granian_stderr.read_text(
                encoding="utf-8", errors="replace"
            )[-6000:]
        except OSError:
            tail = ""
        err = repr(exc)
        if tail.strip():
            err = f"{err}\n--- granian stderr (tail) ---\n{tail}"
        return {"ok": False, "error": err}
    finally:
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()
        stderr_fp.close()
        shutil.rmtree(log_dir, ignore_errors=True)


def _pkg_ver(name: str) -> str:
    try:
        return dist_version(name)
    except PackageNotFoundError:
        return "(not installed)"


def versions_meta() -> dict[str, Any]:
    gv = subprocess.run(
        [GRANIAN_EXE, "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    ov = subprocess.run(
        ["oha", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    granian_line = (gv.stdout or gv.stderr).strip()
    return {
        "python_version": platform.python_version(),
        "granian_version": granian_line,
        "granian": granian_line,
        "oha": (ov.stdout or ov.stderr).strip(),
        "library_versions": {
            "rapis": _pkg_ver("rapis"),
            "litestar": _pkg_ver("litestar"),
            "fastapi": _pkg_ver("fastapi"),
            "emmett": _pkg_ver("emmett"),
            "msgspec": _pkg_ver("msgspec"),
            "pydantic": _pkg_ver("pydantic"),
        },
    }


def main() -> None:
    results: dict[str, Any] = {
        "meta": {
            **versions_meta(),
            "duration": BENCH_DURATION,
            "connections": BENCH_CONNECTIONS,
            "routing_target_index": TARGET_ROUTE_INDEX,
            "route_count": int(os.environ.get("BENCH_ROUTE_COUNT", "256")),
            "interfaces_note": (
                "rapis & Emmett: Granian RSGI; Litestar & FastAPI: Granian ASGI."
            ),
        },
        "runs": [],
    }

    for fw in FRAMEWORKS:
        for sc in SCENARIOS:
            label = f"{fw['id']} / {sc['id']}"
            print(f"== {label} ==", flush=True)
            row = bench_one(fw, sc)
            results["runs"].append(
                {
                    "framework": fw["id"],
                    "scenario": sc["id"],
                    **row,
                }
            )

    out_path = REPO_ROOT / "benchmarks" / "results.json"
    out_path.write_text(json.dumps(results, indent=2))
    print(f"wrote {out_path}", flush=True)


if __name__ == "__main__":
    main()
