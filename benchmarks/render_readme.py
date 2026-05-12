import json
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

MARK_START = "<!-- BENCHMARK_AUTO_START -->"
MARK_END = "<!-- BENCHMARK_AUTO_END -->"

FRAME_ORDER = ["rapis", "emmett", "litestar", "fastapi async", "fastapi sync"]
SCENARIO_ORDER = ["plain", "validation", "static routing"]

LIBRARY_ORDER = [
    "rapis",
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


def render_tables(by_scenario: dict[str, dict[str, dict]]) -> str:
    lines: list[str] = []
    for sid in SCENARIO_ORDER:
        lines.append(f"#### Scenario `{sid}`")
        lines.append("")
        lines.append(
            "| Framework | RPS | avg ms | p50 ms | p99 ms |\n"
            "|-----------|-----|--------|--------|--------|"
        )
        for fid in FRAME_ORDER:
            cell = by_scenario[sid].get(fid)
            if not cell:
                lines.append(f"| {fid} | — | — | — | — |")
                continue
            if not cell.get("ok"):
                msg = cell.get("error", "")[:120]
                lines.append(f"| {fid} | — | — | — | — ({msg}) |")
                continue
            lines.append(
                f"| {fid} | {cell['rps']} | {cell['avg_ms']} | "
                f"{cell['p50_ms']} | {cell['p99_ms']} |"
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
