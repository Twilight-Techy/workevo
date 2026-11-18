"""Render recorded software results without executing workflows or model calls.

uv run --with matplotlib==3.11.2 python scripts/render_benchmarks.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path

METHODS = (
    ("unchanged_seed", "Unchanged seed", "#779487"),
    ("authored_reference", "Authored reference", "#a4c7de"),
    ("random_edits", "Random edits", "#e2c591"),
    ("development_feedback", "Development feedback", "#a5e8bb"),
    ("instruction_only", "Instruction-only", "#779487"),
)
ROOT = Path(__file__).resolve().parents[1]


def render(source: Path, output: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    data = json.loads(source.read_text())
    if data["protocol"]["evidence_kind"] != "authored_software_fixture":
        raise ValueError("this figure is specifically labeled for the authored software fixture")
    if set(data["aggregates"]) != {method for method, _, _ in METHODS}:
        raise ValueError("update the figure labels for the recorded policy set")
    values = []
    for method, label, color in METHODS:
        records = [row for row in data["records"] if row["method"] == method]
        quality = [row["final_quality"] for row in records]
        calls = [row["report"]["usage"]["tool_calls"] for row in records]
        trials = [row["report"]["usage"]["trials"] for row in records]
        measured = {
            "mean_quality": statistics.mean(quality),
            "min_quality": min(quality),
            "max_quality": max(quality),
            "mean_tool_calls": statistics.mean(calls),
            "mean_trials": statistics.mean(trials),
        }
        if not all(
            math.isclose(value, data["aggregates"][method][key], abs_tol=1e-12)
            for key, value in measured.items()
        ):
            raise ValueError(f"aggregate/per-run mismatch for {method}")
        values.append({"method": method, "label": label, "color": color, **measured})
    if (
        len(data["records"]) != data["runs"]
        or sum(row["report"]["usage"]["trials"] for row in data["records"]) != data["trials"]
    ):
        raise ValueError("recorded run/trial totals disagree")

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "svg.fonttype": "none",
            "svg.hashsalt": "workevo-recorded-benchmarks-v1",
            "text.color": "#e7f1e9",
            "axes.labelcolor": "#bdcfc2",
            "xtick.color": "#9db4a5",
            "ytick.color": "#d2e0d5",
            "axes.edgecolor": "#344b3e",
            "font.size": 12,
        }
    )
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.8), gridspec_kw={"width_ratios": [1.18, 1]})
    fig.set_facecolor("#10201a")
    fig.subplots_adjust(left=0.215, right=0.945, top=0.72, bottom=0.23, wspace=0.28)
    fig.text(
        0.045,
        0.92,
        "THE INCLUDED SOFTWARE BENCHMARK",
        color="#a5e8bb",
        size=11,
        weight="bold",
        fontfamily="DejaVu Sans",
        va="top",
    )
    fig.text(0.045, 0.855, "Correctness, with the search expense in view", size=21, weight="bold")
    fig.text(
        0.045,
        0.795,
        f"{data['runs']} runs  /  {data['trials']:,} trials  /  24 authored cases  /  no model calls",
        size=11,
        color="#adc3b3",
    )
    positions = np.arange(len(values))
    for axis in axes:
        axis.set_facecolor("#10201a")
        axis.set_axisbelow(True)
        axis.grid(axis="x", color="#2c4236", linewidth=0.8)
        for spine in axis.spines.values():
            spine.set_visible(False)
        axis.tick_params(axis="both", length=0, pad=10)
        axis.set_yticks(positions)
        axis.invert_yaxis()
    axes[0].set_yticklabels([row["label"] for row in values])
    axes[1].set_yticklabels([])
    axes[0].set_title("Mean final-test correctness", fontsize=12, loc="left", pad=19)
    axes[1].set_title("Mean total operator calls / run", fontsize=12, loc="left", pad=19)
    axes[0].barh(
        positions,
        [row["mean_quality"] * 100 for row in values],
        height=0.48,
        color=[row["color"] for row in values],
        zorder=2,
    )
    axes[1].barh(
        positions,
        [row["mean_tool_calls"] for row in values],
        height=0.48,
        color=[row["color"] for row in values],
        zorder=2,
    )
    for index, row in enumerate(values):
        quality = row["mean_quality"] * 100
        axes[0].text(
            max(quality, row["max_quality"] * 100) + 2.5,
            index,
            f"{quality:g}%",
            va="center",
            size=11,
        )
        axes[1].text(
            row["mean_tool_calls"] + 3, index, f"{row['mean_tool_calls']:g}", va="center", size=11
        )
        if row["min_quality"] != row["max_quality"]:
            axes[0].errorbar(
                quality,
                index,
                xerr=[[quality - row["min_quality"] * 100], [row["max_quality"] * 100 - quality]],
                fmt="none",
                capsize=5,
                ecolor="#f5e7cb",
                elinewidth=1.5,
                zorder=3,
            )
    axes[0].set_xlim(0, 120)
    axes[0].set_xticks([0, 25, 50, 75, 100], labels=["0", "25", "50", "75", "100%"])
    axes[1].set_xlim(0, 166)
    axes[1].set_xticks([0, 50, 100, 150])
    fig.text(
        0.045,
        0.12,
        "Five seed settings per policy. Whisker = observed min–max, not a confidence interval.",
        size=10.2,
        color="#b5c9bb",
    )
    fig.text(
        0.045,
        0.072,
        "Reference is handwritten. Call totals include development, validation and final test.",
        size=10.2,
        color="#b5c9bb",
    )
    fig.text(
        0.045,
        0.025,
        "Authored fixture checks software behavior; it does not establish broad model improvement.",
        size=10.2,
        color="#a5e8bb",
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        output,
        metadata={
            "Date": None,
            "Creator": "workevo / Matplotlib",
            "Title": "Recorded authored-fixture benchmark results",
        },
    )
    plt.close(fig)
    provenance = {
        "schema_version": 1,
        "source": str(source.relative_to(ROOT)),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "renderer": "scripts/render_benchmarks.py",
        "matplotlib": matplotlib.__version__,
        "runs": data["runs"],
        "trials": data["trials"],
        "plotted_values": values,
        "new_model_calls": 0,
        "whisker": "observed seed-setting range; not a confidence interval",
    }
    output.with_suffix(".json").write_text(json.dumps(provenance, indent=2) + "\n")
    print(
        json.dumps(
            {
                "figure": str(output.relative_to(ROOT)),
                "runs": data["runs"],
                "trials": data["trials"],
                "new_model_calls": 0,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "reports/software-study.json")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/assets/benchmark-results.svg")
    args = parser.parse_args()
    render(args.source.resolve(), args.output.resolve())
