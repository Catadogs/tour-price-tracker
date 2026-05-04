"""Generate PNG price charts from SQLite price history."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from price_monitor import storage


def generate_price_chart(
    db_path: Path,
    output_dir: Path,
) -> Path | None:
    """Generate one PNG chart per search target showing price history.

    Returns path to generated PNG, or None if insufficient data.
    """
    grouped = storage.load_price_history_grouped(db_path)
    if not grouped:
        return None

    output_dir.mkdir(parents=True, exist_ok=True)

    charts_generated = 0
    last_chart_path: Path | None = None

    for target_name, by_date in grouped.items():
        chart_path = _chart_for_target(target_name, by_date, output_dir)
        if chart_path:
            charts_generated += 1
            last_chart_path = chart_path

    if charts_generated == 0:
        return None

    logging.info(
        "Price charts generated: %d target(s), saved to %s",
        charts_generated,
        output_dir,
    )
    return last_chart_path


def _chart_for_target(
    target_name: str,
    by_date: dict[str, dict[int, list[tuple[str, int]]]],
    output_dir: Path,
) -> Path | None:
    """Generate a chart for a single search target."""
    # Collect plot lines: one line per (date, nights) pair
    plot_lines: list[tuple[str, list[datetime], list[int]]] = []

    for date, by_nights in by_date.items():
        for nights, points in by_nights.items():
            if len(points) < 2:
                continue
            x = [datetime.fromisoformat(p[0]) for p in points]
            y = [p[1] for p in points]
            label = f"{date} / {nights}н"
            plot_lines.append((label, x, y))

    if not plot_lines:
        return None

    # Limit chart to most recent 30 days of data
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    safe_name = "".join(c if c.isalnum() or c in "_- " else "_" for c in target_name)
    output_path = output_dir / f"chart_{safe_name}.png"

    fig, ax = plt.subplots(figsize=(12, 7))

    colors = [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
        "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
    ]

    for i, (label, x, y) in enumerate(plot_lines):
        color = colors[i % len(colors)]
        filtered_x = [t for t in x if t >= cutoff]
        filtered_y = [y[j] for j, t in enumerate(x) if t >= cutoff]
        if len(filtered_x) < 2:
            continue
        ax.plot(
            filtered_x, filtered_y,
            marker="o" if len(filtered_x) <= 8 else "",
            label=label, color=color,
            linewidth=2, markersize=4,
        )

    # Formatting
    ax.set_xlabel("Дата проверки", fontsize=11)
    ax.set_ylabel("Цена, RUB", fontsize=11)
    ax.set_title(f"История цен — {target_name}", fontsize=13, fontweight="bold")
    ax.grid(True, alpha=0.25, linestyle="--")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    fig.autofmt_xdate(rotation=30, ha="right")

    # Format y-axis with thousand separators
    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda v, _: f"{v:,.0f}".replace(",", " "))
    )

    # Legend inside the chart, transparent background
    ax.legend(
        fontsize=8,
        loc="upper left",
        framealpha=0.7,
        ncol=2 if len(plot_lines) > 6 else 1,
    )

    fig.tight_layout(pad=2)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    return output_path


def prune_old_charts(output_dir: Path, max_age_days: int = 30) -> None:
    """Delete chart PNGs older than max_age_days."""
    if not output_dir.exists():
        return
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    for png in output_dir.glob("*.png"):
        try:
            if datetime.fromtimestamp(png.stat().st_mtime, tz=timezone.utc) < cutoff:
                png.unlink()
        except OSError:
            pass
