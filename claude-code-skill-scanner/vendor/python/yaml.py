"""Minimal YAML loader for offline skill runtime.

Supported subset:
- mappings: key: value
- nested mappings/lists by indentation
- list items: - value / - key: value
- inline lists: [a, b, "c"]
- scalars: strings, bool, null, numbers

This module is intentionally minimal and only targets the YAML shapes used by
SKILL.md frontmatter and skill_scanner rule signatures.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Any


@dataclass
class _Line:
    indent: int
    text: str


class YAMLError(ValueError):
    """Raised when YAML parsing fails."""


def _strip_comment(line: str) -> str:
    in_single = False
    in_double = False
    escaped = False

    for idx, ch in enumerate(line):
        if escaped:
            escaped = False
            continue

        if ch == "\\":
            escaped = True
            continue

        if ch == "'" and not in_double:
            in_single = not in_single
            continue

        if ch == '"' and not in_single:
            in_double = not in_double
            continue

        if ch == "#" and not in_single and not in_double:
            return line[:idx]

    return line


def _split_key_value(text: str) -> tuple[str, str] | None:
    in_single = False
    in_double = False
    escaped = False
    bracket_depth = 0

    for idx, ch in enumerate(text):
        if escaped:
            escaped = False
            continue

        if ch == "\\":
            escaped = True
            continue

        if ch == "'" and not in_double:
            in_single = not in_single
            continue

        if ch == '"' and not in_single:
            in_double = not in_double
            continue

        if in_single or in_double:
            continue

        if ch == "[":
            bracket_depth += 1
            continue

        if ch == "]" and bracket_depth > 0:
            bracket_depth -= 1
            continue

        if ch == ":" and bracket_depth == 0:
            key = text[:idx].strip()
            value = text[idx + 1 :].strip()
            return key, value

    return None


def _split_inline_list(text: str) -> list[str]:
    items: list[str] = []
    current: list[str] = []
    in_single = False
    in_double = False
    escaped = False
    bracket_depth = 0

    for ch in text:
        if escaped:
            current.append(ch)
            escaped = False
            continue

        if ch == "\\":
            current.append(ch)
            escaped = True
            continue

        if ch == "'" and not in_double:
            in_single = not in_single
            current.append(ch)
            continue

        if ch == '"' and not in_single:
            in_double = not in_double
            current.append(ch)
            continue

        if not in_single and not in_double:
            if ch == "[":
                bracket_depth += 1
            elif ch == "]" and bracket_depth > 0:
                bracket_depth -= 1
            elif ch == "," and bracket_depth == 0:
                item = "".join(current).strip()
                if item:
                    items.append(item)
                current = []
                continue

        current.append(ch)

    tail = "".join(current).strip()
    if tail:
        items.append(tail)

    return items


def _parse_scalar(raw: str) -> Any:
    raw = raw.strip()

    if raw == "":
        return ""

    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(item) for item in _split_inline_list(inner)]

    if (raw.startswith("\"") and raw.endswith("\"")) or (raw.startswith("'") and raw.endswith("'")):
        try:
            return ast.literal_eval(raw)
        except Exception:
            return raw[1:-1]

    lowered = raw.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "none", "~"}:
        return None

    try:
        if any(token in raw for token in [".", "e", "E"]):
            return float(raw)
        return int(raw)
    except ValueError:
        return raw


def _preprocess(text: str) -> list[_Line]:
    processed: list[_Line] = []

    for raw_line in text.splitlines():
        no_comment = _strip_comment(raw_line)
        if not no_comment.strip():
            continue

        indent = len(no_comment) - len(no_comment.lstrip(" "))
        stripped = no_comment.strip()
        processed.append(_Line(indent=indent, text=stripped))

    return processed


def safe_load(stream: Any) -> Any:
    if hasattr(stream, "read"):
        text = stream.read()
    else:
        text = str(stream)

    lines = _preprocess(text)
    if not lines:
        return None

    idx = 0

    def parse_block(expected_indent: int) -> Any:
        nonlocal idx
        if idx >= len(lines):
            return None

        current = lines[idx]
        if current.indent < expected_indent:
            return None

        if current.text.startswith("- "):
            return parse_list(expected_indent)
        return parse_dict(expected_indent)

    def parse_dict(expected_indent: int) -> dict[str, Any]:
        nonlocal idx
        out: dict[str, Any] = {}

        while idx < len(lines):
            line = lines[idx]
            if line.indent < expected_indent:
                break
            if line.indent > expected_indent:
                raise YAMLError(f"Unexpected indentation at line: {line.text}")
            if line.text.startswith("- "):
                break

            pair = _split_key_value(line.text)
            if pair is None:
                raise YAMLError(f"Invalid mapping entry: {line.text}")

            key, value_raw = pair
            idx += 1

            if value_raw == "":
                if idx < len(lines) and lines[idx].indent > line.indent:
                    out[key] = parse_block(lines[idx].indent)
                else:
                    out[key] = None
            else:
                out[key] = _parse_scalar(value_raw)

        return out

    def parse_list(expected_indent: int) -> list[Any]:
        nonlocal idx
        out: list[Any] = []

        while idx < len(lines):
            line = lines[idx]
            if line.indent < expected_indent:
                break
            if line.indent != expected_indent or not line.text.startswith("- "):
                break

            raw_item = line.text[2:].strip()
            idx += 1

            if raw_item == "":
                if idx < len(lines) and lines[idx].indent > line.indent:
                    out.append(parse_block(lines[idx].indent))
                else:
                    out.append(None)
                continue

            pair = _split_key_value(raw_item)
            if pair is None:
                out.append(_parse_scalar(raw_item))
                continue

            key, value_raw = pair
            item: dict[str, Any] = {}

            if value_raw == "":
                if idx < len(lines) and lines[idx].indent > line.indent:
                    item[key] = parse_block(lines[idx].indent)
                else:
                    item[key] = None
            else:
                item[key] = _parse_scalar(value_raw)

            while idx < len(lines):
                nested = lines[idx]
                if nested.indent <= line.indent:
                    break
                if nested.text.startswith("- "):
                    break

                nested_pair = _split_key_value(nested.text)
                if nested_pair is None:
                    raise YAMLError(f"Invalid nested mapping entry: {nested.text}")

                nested_key, nested_value_raw = nested_pair
                idx += 1

                if nested_value_raw == "":
                    if idx < len(lines) and lines[idx].indent > nested.indent:
                        item[nested_key] = parse_block(lines[idx].indent)
                    else:
                        item[nested_key] = None
                else:
                    item[nested_key] = _parse_scalar(nested_value_raw)

            out.append(item)

        return out

    root = parse_block(lines[0].indent)

    if idx < len(lines):
        raise YAMLError(f"Failed to parse YAML near: {lines[idx].text}")

    return root
