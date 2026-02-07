"""Minimal python-frontmatter replacement for offline runtime."""

from __future__ import annotations

from dataclasses import dataclass

import yaml


@dataclass
class Post:
    metadata: dict
    content: str


def loads(text: str) -> Post:
    text = text or ""
    if not text.startswith("---"):
        return Post(metadata={}, content=text)

    lines = text.splitlines()
    if not lines:
        return Post(metadata={}, content="")

    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        raise ValueError("Invalid frontmatter: missing closing '---'")

    header = "\n".join(lines[1:end_idx])
    body = "\n".join(lines[end_idx + 1 :])

    metadata = yaml.safe_load(header) or {}
    if not isinstance(metadata, dict):
        raise ValueError("Invalid frontmatter: metadata must be a mapping")

    return Post(metadata=metadata, content=body)
