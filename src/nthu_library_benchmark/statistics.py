from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from statistics import mean, quantiles, stdev


@dataclass(frozen=True)
class Summary:
    """Descriptive statistics for recorded DOM readiness times."""

    count: int
    minimum: float
    first_quartile: float
    median: float
    third_quartile: float
    maximum: float
    average: float
    standard_deviation: float | None


class Statistics:
    """Collect DOM readiness times and render a text-based report."""

    def __init__(self, *, chart_bins: int = 8, chart_width: int = 32) -> None:
        if chart_bins < 1:
            raise ValueError("chart_bins must be greater than zero")
        if chart_width < 1:
            raise ValueError("chart_width must be greater than zero")
        self.chart_bins = chart_bins
        self.chart_width = chart_width
        self._dom_elapsed: list[float] = []

    def add(self, dom_elapsed: float) -> None:
        """Add one non-negative DOM readiness duration in seconds."""
        if not isfinite(dom_elapsed) or dom_elapsed < 0:
            raise ValueError("dom_elapsed must be a finite, non-negative number")
        self._dom_elapsed.append(dom_elapsed)

    def summarize(self) -> Summary | None:
        """Return descriptive statistics, or None when no values exist."""
        if not self._dom_elapsed:
            return None

        values = sorted(self._dom_elapsed)
        quartiles = (
            quantiles(values, n=4, method="inclusive")
            if len(values) > 1
            else [values[0]] * 3
        )
        return Summary(
            count=len(values),
            minimum=values[0],
            first_quartile=quartiles[0],
            median=quartiles[1],
            third_quartile=quartiles[2],
            maximum=values[-1],
            average=mean(values),
            standard_deviation=stdev(values) if len(values) > 1 else None,
        )

    def format_report(self) -> str:
        """Render summary statistics and an ASCII histogram."""
        summary = self.summarize()
        if summary is None:
            return "DOM elapsed statistics\nNo completed measurements."

        standard_deviation = (
            f"{summary.standard_deviation:.3f}s"
            if summary.standard_deviation is not None
            else "N/A (one measurement)"
        )
        lines = [
            "DOM elapsed statistics",
            f"count: {summary.count}",
            f"average: {summary.average:.3f}s",
            f"standard deviation (sample): {standard_deviation}",
            f"minimum: {summary.minimum:.3f}s",
            f"Q1: {summary.first_quartile:.3f}s",
            f"median: {summary.median:.3f}s",
            f"Q3: {summary.third_quartile:.3f}s",
            f"maximum: {summary.maximum:.3f}s",
            "",
            self._format_histogram(),
        ]
        return "\n".join(lines)

    def write_report(self, path: str | Path) -> Path:
        """Write the formatted report, including its histogram, to a file."""
        report_path = Path(path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(self.format_report() + "\n", encoding="utf-8")
        return report_path

    def _format_histogram(self) -> str:
        values = self._dom_elapsed
        minimum = min(values)
        maximum = max(values)
        if minimum == maximum:
            return f"histogram ({minimum:.3f}s): {'#' * self.chart_width}"

        bin_size = (maximum - minimum) / self.chart_bins
        counts = [0] * self.chart_bins
        for value in values:
            index = min(int((value - minimum) / bin_size), self.chart_bins - 1)
            counts[index] += 1

        largest_count = max(counts)
        lines = ["histogram (seconds):"]
        for index, count in enumerate(counts):
            start = minimum + index * bin_size
            end = maximum if index == self.chart_bins - 1 else start + bin_size
            bar_length = round(count / largest_count * self.chart_width)
            lines.append(
                f"{start:7.3f}-{end:7.3f} | {'#' * bar_length} ({count})"
            )
        return "\n".join(lines)
