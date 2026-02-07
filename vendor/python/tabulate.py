"""Minimal tabulate replacement for offline runtime."""

from __future__ import annotations

from typing import Iterable, Sequence


def tabulate(rows: Iterable[Sequence], headers: Sequence | None = None, tablefmt: str = "simple") -> str:
    data = [list(map(_stringify, row)) for row in rows]
    head = list(map(_stringify, headers)) if headers else []

    width_count = max(len(head), max((len(r) for r in data), default=0))
    if width_count == 0:
        return ""

    normalized_rows = [r + [""] * (width_count - len(r)) for r in data]
    normalized_head = head + [""] * (width_count - len(head)) if head else None

    widths = [0] * width_count
    for row in normalized_rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    if normalized_head:
        for i, cell in enumerate(normalized_head):
            widths[i] = max(widths[i], len(cell))

    lines = []
    if normalized_head:
        lines.append(_fmt_row(normalized_head, widths))
        lines.append("-+-".join("-" * w for w in widths))

    for row in normalized_rows:
        lines.append(_fmt_row(row, widths))

    return "\n".join(lines)


def _fmt_row(row: Sequence[str], widths: Sequence[int]) -> str:
    return " | ".join(cell.ljust(widths[i]) for i, cell in enumerate(row))


def _stringify(value: object) -> str:
    return "" if value is None else str(value)
