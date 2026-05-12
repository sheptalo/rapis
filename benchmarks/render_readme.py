import json
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

MARK_START = "<!-- BENCHMARK_AUTO_START -->"
MARK_END = "<!-- BENCHMARK_AUTO_END -->"

FRAME_ORDER = ["rapis", "emmett", "litestar", "fastapi async", "fastapi sync"]


def load_results(path: Path) -> dict:
    if not path.is_file():
        return {"meta": {}, "runs": []}
    return json.loads(path.read_text())


def chart_block(
    title: str, y_title: str, labels: list[str], values: list[float]
) -> str:
    vmax = max(values + [1e-9])
    if vmax >= 50:
        ymax = int(vmax * 1.12) + 1
    else:
        ymax = max(1.0, round(vmax * 1.35 + 1e-6, 4))
    vals = ", ".join(str(round(v, 2)) for v in values)
    labs = ", ".join(labels)
    safe_title = title.replace('"', "'")
    return f"""### {title}

```mermaid
xychart-beta
    title "{safe_title}"
    x-axis [{labs}]
    y-axis "{y_title}" 0 --> {ymax}
    bar [{vals}]
```
"""


def render_tables(by_scenario: dict[str, dict[str, dict]]) -> str:
    lines: list[str] = []
    for sid in ["plain", "validation", "static routing"]:
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
                lines.append(
                    f"| {fid} | — | — | — | — `{cell.get('error', '')}` |"
                )
                continue
            lines.append(
                f"| {fid} | {cell['rps']} | {cell['avg_ms']} | "
                f"{cell['p50_ms']} | {cell['p99_ms']} |"
            )
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

    sections.append("_Latest automated numbers (see workflow «Benchmarks»)._")
    sections.append("")
    sections.append("#### Environment snapshot")
    sections.append("")
    sections.append("| Setting | Value |")
    sections.append("|---------|-------|")
    for key in ("granian", "oha", "duration", "connections", "route_count"):
        if key in meta:
            sections.append(f"| `{key}` | {meta[key]} |")  # noqa: PERF401
    if "routing_target_index" in meta:
        sections.append(
            f"| routing probe path | `/bench/r/{meta['routing_target_index']}` |"  # noqa: E501
        )
    if "interfaces_note" in meta:
        sections.append(f"| interfaces | {meta['interfaces_note']} |")
    sections.append("")
    sections.append(render_tables(by_scenario))

    chart_specs = [
        ("plain", "Throughput — scenario plain", "rps", "requests/sec"),
        (
            "validation",
            "Throughput validation",
            "rps",
            "requests/sec",
        ),
        (
            "static routing",
            "Throughput static routing (high - better)",
            "rps",
            "requests/sec",
        ),
        (
            "plain",
            "Latency p50 — scenario plain (lower - better)",
            "p50_ms",
            "ms",
        ),
        (
            "validation",
            "Latency p50 validation (lower - better)",
            "p50_ms",
            "ms",
        ),
        (
            "static routing",
            "Latency p50 static routing (lower - better)",
            "p50_ms",
            "ms",
        ),
    ]

    for sid, title, metric_key, y_label in chart_specs:
        labels = FRAME_ORDER.copy()
        values: list[float] = []
        for fid in FRAME_ORDER:
            row = by_scenario[sid].get(fid)
            if row and row.get("ok"):
                values.append(float(row[metric_key]))
            else:
                values.append(0.0)
        sections.append(chart_block(title, y_label, labels, values))
        sections.append("")

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
