import json
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
_REPO_STR = str(REPO_ROOT)
if _REPO_STR not in sys.path:
    sys.path.insert(0, _REPO_STR)

from benchmarks.run_benchmarks import SCENARIOS

MARK_START = "<!-- BENCHMARK_AUTO_START -->"
MARK_END = "<!-- BENCHMARK_AUTO_END -->"

FRAME_ORDER = ["rapis", "emmett", "sanic", "litestar", "fastapi async", "fastapi sync"]

SCENARIO_ORDER = [s["id"] for s in SCENARIOS]

LIBRARY_ORDER = [
    "rapis",
    "sanic",
    "litestar",
    "fastapi",
    "emmett",
    "msgspec",
    "pydantic",
]


def load_results(path: Path) -> dict:
    if not path.is_file():
        return {"meta": {}, "runs": []}
    return json.loads(path.read_text())


def _baseline_rps(rapis_cell: dict | None) -> float | None:
    if not rapis_cell or not rapis_cell.get("ok"):
        return None
    rps = rapis_cell.get("rps")
    if rps is None:
        return None
    try:
        v = float(rps)
    except (TypeError, ValueError):
        return None
    if v <= 0:
        return None
    return v


def _format_ratio(fid: str, cell: dict, baseline: float | None) -> str:
    if baseline is None:
        return "—"
    if fid == "fastapi async":
        return "1.00"
    if not cell.get("ok"):
        return "—"
    rps = cell.get("rps", 0)
    try:
        v = float(rps)
    except (TypeError, ValueError):
        return "—"
    return f"{v / baseline:.2f}"


def _winner_fids_for_metric(
    scenario_cells: dict[str, dict],
    *,
    metric: str,
    mode: str,
) -> set[str]:
    """Collect framework ids tied for best `metric`; `mode` is `max` or `min`.

    Rows in FRAME_ORDER are scanned; ``RANKING_SKIP_FRAMEWORK`` is ignored for ranking.
    """
    pairs: list[tuple[str, float]] = []
    for fid in FRAME_ORDER:
        cell = scenario_cells.get(fid)
        if not cell or not cell.get("ok"):
            continue
        raw = cell.get(metric)
        if raw is None:
            continue
        try:
            pairs.append((fid, float(raw)))
        except (TypeError, ValueError):
            continue
    if not pairs:
        return set()
    if mode == "max":
        bound = max(v for _, v in pairs)
    else:
        bound = min(v for _, v in pairs)
    return {fid for fid, v in pairs if v == bound}


def _bold_cell(text: str, bold: bool) -> str:
    return f"**{text}**" if bold else text


def render_tables(by_scenario: dict[str, dict[str, dict]]) -> str:
    lines: list[str] = []
    for sid in SCENARIO_ORDER:
        lines.append(f"#### Scenario `{sid}`")
        lines.append("")
        cells = by_scenario[sid]
        baseline = _baseline_rps(cells.get("fastapi async"))

        win_rps = _winner_fids_for_metric(cells, metric="rps", mode="max")
        win_avg = _winner_fids_for_metric(cells, metric="avg_ms", mode="min")
        win_p50 = _winner_fids_for_metric(cells, metric="p50_ms", mode="min")
        win_p99 = _winner_fids_for_metric(cells, metric="p99_ms", mode="min")
        # ratio is proportional to RPS vs fixed baseline → same leaders as `rps`.
        win_ratio = win_rps if baseline is not None else set()

        def row_highlights(fid: str) -> tuple[bool, bool, bool, bool, bool]:
            return (
                fid in win_rps,
                fid in win_ratio,
                fid in win_avg,
                fid in win_p50,
                fid in win_p99,
            )

        lines.append(
            "| Framework | RPS | ratio | avg ms | p50 ms | p99 ms |\n"
            "|-----------|-----|-------|--------|--------|--------|"
        )
        for fid in FRAME_ORDER:
            cell = by_scenario[sid].get(fid)
            bh_rps, bh_ratio, bh_avg, bh_p50, bh_p99 = row_highlights(fid)
            ratio = _format_ratio(fid, cell or {}, baseline)
            ratio_cell = _bold_cell(ratio, bh_ratio)

            if not cell:
                lines.append(
                    f"| {fid} | — | {ratio_cell} | — | — | — |"
                )
                continue
            if not cell.get("ok"):
                msg = cell.get("error", "")[:120]
                lines.append(
                    f"| {fid} | — | {ratio_cell} | — | — | — ({msg}) |"
                )
                continue
            rps_cell = _bold_cell(str(cell["rps"]), bh_rps)
            avg_cell = _bold_cell(str(cell["avg_ms"]), bh_avg)
            p50_cell = _bold_cell(str(cell["p50_ms"]), bh_p50)
            p99_cell = _bold_cell(str(cell["p99_ms"]), bh_p99)
            lines.append(
                f"| {fid} | {rps_cell} | {ratio_cell} | "
                f"{avg_cell} | {p50_cell} | {p99_cell} |"
            )
        lines.append("")
    return "\n".join(lines)


def render_environment(meta: dict) -> str:
    lines = [
        "#### Runtime & load",
        "",
        "| Field | Value |",
        "|-------|-------|",
    ]
    if "python_version" in meta:
        lines.append(f"| Python | `{meta['python_version']}` |")
    gv = meta.get("granian_version") or meta.get("granian")
    if gv:
        lines.append(f"| Granian | `{gv}` |")
    if "oha" in meta:
        lines.append(f"| oha | `{meta['oha']}` |")
    if "duration" in meta:
        lines.append(f"| Load duration `-z` | `{meta['duration']}` |")
    if "connections" in meta:
        lines.append(f"| Connections `-c` | `{meta['connections']}` |")
    if "route_count" in meta:
        lines.append(f"| Static routes (`BENCH_ROUTE_COUNT`) | `{meta['route_count']}` |")
    if "routing_target_index" in meta:
        lines.append(
            "| Routing probe URL | `/bench/r/"
            f"{meta['routing_target_index']}` |"
        )
    if "interfaces_note" in meta:
        lines.append(f"| Interfaces | {meta['interfaces_note']} |")
    lines.append("")

    libs = meta.get("library_versions") or {}
    if libs:
        lines.extend(
            [
                "#### Framework & library packages (PyPI)",
                "",
                "| Package | Version |",
                "|---------|---------|",
            ]
        )
        seen: set[str] = set()
        for name in LIBRARY_ORDER:
            if name not in libs or name in seen:
                continue
            seen.add(name)
            lines.append(f"| `{name}` | `{libs[name]}` |")
        for name, ver in sorted(libs.items()):
            if name not in seen:
                lines.append(f"| `{name}` | `{ver}` |")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    results_path = REPO_ROOT / "benchmarks" / "results.json"
    readme_path = REPO_ROOT / "benchmarks" / "README.md"
    data = load_results(results_path)

    runs = data.get("runs", [])
    meta = data.get("meta", {})

    by_scenario: dict[str, dict[str, dict]] = defaultdict(dict)
    for row in runs:
        by_scenario[row["scenario"]][row["framework"]] = row

    sections: list[str] = []

    sections.append("_Latest automated numbers (workflow «Benchmarks»)._")
    sections.append("")
    sections.append(render_environment(meta))
    sections.append(render_tables(by_scenario))

    auto_body = "\n".join(sections).strip() + "\n"

    template = readme_path.read_text()
    if MARK_START not in template or MARK_END not in template:
        raise SystemExit(
            f"{readme_path} must contain {MARK_START} and {MARK_END}"
        )
    head, rest = template.split(MARK_START, 1)
    _, tail = rest.split(MARK_END, 1)
    new_content = (
        f"{head.rstrip()}\n\n{MARK_START}\n\n"
        f"{auto_body}\n{MARK_END}\n{tail.lstrip()}"
    )
    readme_path.write_text(new_content)


if __name__ == "__main__":
    main()
