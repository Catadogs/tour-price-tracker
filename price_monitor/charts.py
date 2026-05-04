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
    """Generate a PNG chart of price history per target/date/nights.

    Returns path to generated PNG, or None if insufficient data.
    """
    grouped = storage.load_price_history_grouped(db_path)
    if not grouped:
        return None

    # Flatten for plotting: collect all lines (target, date, nights) -> (x, y)
    plot_lines: list[tuple[str, list[datetime], list[int]]] = []
    for target_name, by_date in grouped.items():
        for date, by_nights in by_date.items():
            for nights, points in by_nights.items():
                if len(points) < 2:
                    continue
                x = [datetime.fromisoformat(p[0]) for p in points]
                y = [p[1] for p in points]
                label = f"{target_name} / {date} / {nights}н"
                plot_lines.append((label, x, y))

    if not plot_lines:
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "price_chart.png"

    fig, ax = plt.subplots(figsize=(10, 6))
    colors = plt.cm.tab10.colors  # type: ignore[attr-defined]

    for i, (label, x, y) in enumerate(plot_lines):
        color = colors[i % len(colors)]
        ax.plot(x, y, marker="o", label=label, color=color, linewidth=1.5, markersize=3)

    ax.set_xlabel("Дата")
    ax.set_ylabel("Цена (RUB)")
    ax.set_title("История цен")
    ax.legend(fontsize=7, loc="upper left", bbox_to_anchor=(1, 1))
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
    fig.autofmt_xdate()
    fig.tight_layout()

    fig.savefig(output_path, dpi=100, bbox_inches="tight")
    plt.close(fig)

    logging.info("Price chart saved to %s (%d lines)", output_path, len(plot_lines))
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
